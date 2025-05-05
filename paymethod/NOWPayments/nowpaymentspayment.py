#!/usr/bin/python3
import sys
import json
import os
from typing import Dict, List

sys.path.insert(0, "/usr/local/mgr5/lib/python")

import billmgr.db
import billmgr.logger as logging
import billmgr.exception

from billmgr import payment
from billmgr.modules.paymentcgi import PageType, PaymentCgi, PaymentCgiType, run_cgi

from nowpayments.api import NOWPaymentsAPI
from nowpayments.exceptions import InvalidResponseException


logging.init_logging("nowpaymentspayment")
logger = logging.get_logger("nowpaymentspayment")


class NOWPaymentsPaymentCgi(PaymentCgi):
    def cgi_type(self) -> PaymentCgiType:
        return PaymentCgiType.Payment

    def process(self):
        logger.info("run payment cgi")

        api_key: str = self.paymethod_params["api_key"]
        is_test: bool = False if self.paymethod_params["test"] == "off" else True

        api = NOWPaymentsAPI(api_key=api_key, is_test=is_test)

        if not api.is_api_ok():
            logger.info(
                "API is down; unable to redirect to link")
            self.redirect_to_url(self.get_page(PageType.Fail))
            return

        # get the url if payment already exists
        if int(self.payment_params["status"]) == int(payment.PaymentStatus.psInPay.value):
            logger.info("payment already in pay")

            invoice_url = self.get_unfinished_payment_url(
                self.payment_params, self.paymethod_params, api)

            logger.info(f"invoice url = {invoice_url}")

            self.redirect_to_url(invoice_url)

        # else generate a new url using NOWPayments API (basically assuming status NEWLY_CREATED)
        else:
            payment_amount = float(self.payment_params["paymethodamount"])
            order_id = self.payment_params["number"]
            description = self.payment_params["description"]

            currency = billmgr.db.get_first_record(f"""
                SELECT iso FROM currency
                WHERE id = {self.paymethod_params["currency"]}
            """)

            if currency is None:
                raise billmgr.exception.XmlException("missed_currency")

            try:
                invoice: Dict = api.get_invoice(
                    price_amount=payment_amount,
                    price_currency=currency.as_str("iso"),
                    order_id=order_id,
                    description=description,
                    success_url=(f"https://{os.environ['HTTP_HOST']}/mancgi/nowpaymentsresult"
                                 f"?elid={self.payment_params['id']}"),
                    cancel_url=(f"https://{os.environ['HTTP_HOST']}/mancgi/nowpaymentsresult"
                                f"?elid={self.payment_params['id']}")
                )
            except Exception as e:
                raise billmgr.exception.XmlException("no_url_provided") from e

            # invoice id of payment on NOWPayments is assigned to billmgr payment as externalid
            payment.set_in_pay(
                int(self.elid()),
                info="",
                external_id=str(invoice.get("id"))
            )

            self.redirect_to_url(str(invoice.get("invoice_url")))

    def get_unfinished_payment_url(self, pay: dict, pm: dict, api: NOWPaymentsAPI) -> str:
        """Return url to invoice if payment is INPAY

        Keyword arguments:
        pay -- payment in billmgr
        """
        token = api.get_jwt_token(pm["email"], pm["password"])
        logger.info(token)
        nowpayments: List = []

        try:
            nowpayments = api.get_payments_by_invoice(token, pay["externalid"])
        except InvalidResponseException:
            logger.error(
                f"missing payment_id: "
                f"failed to retrieve payments for the unfinished payment {json.dumps(pay)} "
                f"and paymethod {json.dumps(pm)} while getting url when in pay")

        logger.info(nowpayments)

        for nowpay in nowpayments:
            logger.info(nowpay.get("order_id"))
            logger.info(pay["number"])
            logger.info(nowpay.get("order_id") == pay["number"])

            if nowpay.get("order_id") == pay["number"]:
                logger.info(f"payment id {nowpay.get('payment_id')} exists")
                # return if both invoice_id and payment_id have been assigned to
                # this payment
                return (
                    f"{api.get_payment_url()}/?iid={pay['externalid']}"
                    f"&paymentId={nowpay.get('payment_id')}"
                )

        # return if this payment has been initiated but wasn't assigned payment_id
        return f"{api.get_payment_url()}/?iid={pay['externalid']}"


if __name__ == "__main__":
    run_cgi(NOWPaymentsPaymentCgi)
