#!/usr/bin/python3

import sys
from xml.etree import ElementTree

sys.path.insert(0, "/usr/local/mgr5/lib/python")
from billmgr.modules.paymentcgi import PageType, PaymentCgi, PaymentCgiType, run_cgi
import billmgr.logger as logging
import billmgr.db as db
import billmgr.payment as payment

from nowpayments.api import NOWPaymentsAPI
from nowpayments.enums import PaymentStatus


logging.init_logging("nowpaymentsresult")
logger = logging.get_logger("nowpaymentsresult")

PAYMETHOD_MODULE_NAME = "pmnowpayments"


class NOWPaymentsResultCgi(PaymentCgi):
    def __init__(self):
        self._payment_id = 0
        PaymentCgi.__init__(self)

    def cgi_type(self) -> PaymentCgiType:
        return PaymentCgiType.Payment

    def _find_payment(self) -> db.Record:
        return db.get_first_record_unwrap(
            f" SELECT pay.externalid, pm.xmlparams FROM payment AS pay"
            f" JOIN paymethod AS pm ON pay.paymethod = pm.id"
            f" WHERE paymethod IN ("
            f" SELECT id FROM paymethod WHERE module = \"{PAYMETHOD_MODULE_NAME}\")"
            f" AND pay.id = \"{self.elid()}\""
        )

    def parse_input(self):
        self._elid: str = self.input["elid"]

    def elid(self) -> str:
        return str(self._elid)

    def process(self):
        logger.info("run nowpaymentsresult")

        logger.info(self.input)

        _payment = self._find_payment()
        logger.info(_payment)

        params = ElementTree.fromstring(_payment.as_str("xmlparams"))
        logger.info(params)

        external_id = _payment.as_str("externalid")

        api_key: str = params.findtext("api_key", default="")
        is_test: bool = False if params.findtext(
            "test", default="") == "off" else True
        api = NOWPaymentsAPI(api_key, is_test)

        if not api.is_api_ok():
            logger.info(
                "API is down; unable to check immediately")
            self.redirect_to_url(self.get_page(PageType.Pending))
            return

        try:
            token = api.get_jwt_token(
                params.findtext("email", default=""),
                params.findtext("password", default=""))

            logger.info(token)

            nowpayment = api.get_first_payment(
                token, external_id)

            logger.info(f"payment is {nowpayment}")

            status = nowpayment.get("payment_status")
            logger.info(f"status is {status}")

            if status == PaymentStatus.FINISHED:
                payment.set_paid(int(self.elid()), external_id)
                logger.info("paid")
                self.redirect_to_url(self.get_page(PageType.Success))

            elif status in {PaymentStatus.WAITING,
                            PaymentStatus.CONFIRMING,
                            PaymentStatus.CONFIRMED,
                            PaymentStatus.SENDING}:
                payment.set_in_pay(int(self.elid()), external_id)
                logger.info("in_pay")
                self.redirect_to_url(self.get_page(PageType.Pending))

            elif status in {PaymentStatus.FAILED}:
                payment.set_canceled(int(self.elid()), external_id)
                logger.info("canceled")
                self.redirect_to_url(self.get_page(PageType.Fail))

        except Exception:
            logger.error("fail")
            self.redirect_to_url(self.get_page(PageType.Fail))


if __name__ == "__main__":
    run_cgi(NOWPaymentsResultCgi)
