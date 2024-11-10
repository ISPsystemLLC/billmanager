#!/usr/bin/python3
import re
import argparse
import sys
import traceback
from xml.etree import ElementTree
from datetime import timedelta, datetime
from typing import Dict, List, Set

sys.path.insert(0, "/usr/local/mgr5/lib/python")

import billmgr.db
import billmgr.exception
import billmgr.logger as logging
import billmgr.session as session

from billmgr.modules.paymethod import PaymethodModule, Feature, Param
from billmgr import payment


from nowpayments.api import NOWPaymentsAPI
from nowpayments.enums import PaymentStatus
from nowpayments.exceptions import NotOkException, InvalidResponseException


MODULE_NAME = "pmnowpayments"
logging.init_logging(MODULE_NAME)
logger = logging.get_logger(MODULE_NAME)

class NOWPaymentsModule(PaymethodModule):
    def __init__(self):
        super().__init__()
        self._add_feature(Feature.REDIRECT)
        self._add_feature(Feature.NOT_PROFILE)

        self._add_callable_feature(Feature.CHECKPAY, self.check_pay)
        self._add_callable_feature(Feature.PMVALIDATE, self.pm_validate)

        self._add_param(Param.PAYMENT_SCRIPT, "/mancgi/nowpaymentspayment")

    def _on_raise_exception(self, args: argparse.Namespace, err: billmgr.exception.XmlException):
        print(err.as_xml())

    def pm_validate(self):
        logger.info("run pm_validate")

        xml = session.get_input_xml()

        is_test: bool = self.__convert_is_test_to_bool(
            xml.findtext("test", default="on"))
        api_key: str = xml.findtext("api_key", default="")

        api = NOWPaymentsAPI(api_key=api_key, is_test=is_test)

        if not api.is_api_ok():
            logger.info(
                "API is down; unable to create paymethod now")
            raise billmgr.exception.XmlException("api_down")

        email: str = xml.findtext("email", default="")
        psw: str = xml.findtext("password", default="")

        #check whether the email matches the form
        true_email_form = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(true_email_form, email):
            raise billmgr.exception.XmlException("wrong_email_form")
        
        # check if token can be generated (account exists)
        try:
            jwt_token = api.get_jwt_token(email=email, password=psw)
        except Exception as e:
            raise billmgr.exception.XmlException("invalid_auth") from e

        try:
            api.is_valid_api_key()
        except Exception as e:
            raise billmgr.exception.XmlException("invalid_api_key") from e

        try:
            api.is_valid_api_auth(jwt_token)
        except Exception as e:
            raise billmgr.exception.XmlException("invalid_api_auth") from e

    def check_pay(self):
        logger.info("run checkpay")

        from_date: str = (datetime.today() - timedelta(days=10)
                          ).strftime("%Y-%m-%d")
        mgr_payments: List[billmgr.db.Record] = billmgr.db.db_query(f"""
            SELECT p.id, p.paymethodamount, p.externalid, pm.xmlparams,
            p.number, p.createdate FROM payment p
            JOIN paymethod pm ON p.paymethod = pm.id
            WHERE module = "pmnowpayments"
                AND p.status = {payment.PaymentStatus.psInPay.value}
                AND createdate >= "{from_date}"
            ORDER BY pm.xmlparams
        """)

        if len(mgr_payments) == 0:
            logger.info("No payments in mgr database")
            return

        xml_params: Set[str] = {p.as_str("xmlparams") for p in mgr_payments}
        jwt_tokens: Dict[str, str] = {}  # {email: token}
        # payments split by xmlparams
        mgr_payments_split: Dict[str, List[billmgr.db.Record]] = {}

        # split payments by xml params
        for pay in mgr_payments:
            xml = pay.as_str("xmlparams")
            if xml not in mgr_payments_split:
                mgr_payments_split[xml] = []
            mgr_payments_split[xml].append(pay)

        # begin checking payments sorted by xml params
        for xml in xml_params:
            params = ElementTree.fromstring(xml)
            api_key = params.findtext("api_key", default="")
            email = params.findtext("email", default="")
            psw = params.findtext("password", default="")
            is_test: bool = self.__convert_is_test_to_bool(
                params.findtext("test", default="on"))

            api = NOWPaymentsAPI(api_key=api_key, is_test=is_test)

            if not api.is_api_ok():
                logger.info(
                    "API is down. Payments will be checked at a later time")
                return

            if email not in jwt_tokens.keys():
                jwt_token = api.get_jwt_token(email=email, password=psw)
                jwt_tokens[email] = jwt_token
            else:
                jwt_token = jwt_tokens[email]

            # check and assign status for each payment
            for pay in mgr_payments_split[xml]:
                try:
                    logger.info(pay)
                    invoice_id = pay.as_int("externalid")
                    nowpayments = api.get_payments_by_invoice(
                        jwt_token=jwt_token, invoice_id=invoice_id)

                    if len(nowpayments) == 0:
                        logger.info(
                            f"Encountered empty list for invoice id {invoice_id}")

                        self.__set_bill_payment_status(
                            pay.as_int("id"),
                            PaymentStatus.WAITING,
                            invoice_id,
                            pay.as_str("createdate"))

                    for nowpay in nowpayments:
                        logger.info(nowpay)

                        self.__set_bill_payment_status(
                            pay.as_int("id"),
                            nowpay.get("payment_status"),
                            invoice_id,
                            pay.as_str("createdate"))
                        logger.info(
                            f"payment {pay['id']} invoice_id {pay['externalid']} matched")
                except InvalidResponseException:
                    logger.error(
                        f"failed to retrieve payments for payment with externalid {invoice_id} "
                        f"while checking pay"
                    )

                except Exception as error:
                    logger.error(repr(error) + traceback.format_exc())

    def __set_bill_payment_status(self, _id: int, status: str, external_id: int, created_at: str):
        """Set payment status in billmgr depending on the NOWPayment's payment

        Keyword arguments:
        _id -- this payment's elid (billmgr)
        status -- this payment's PaymentStatus (NOWPayments)
        external_id -- this payment's external_id / invoice_id
        created_at -- the day this payment has been created at
        """
        logger.info("set_status")
        if status == PaymentStatus.FINISHED:
            payment.set_paid(_id, info="paid",
                             external_id=f"external_{external_id}")
            logger.info(
                f"paid payment wtih id {_id} and external id {external_id}")

        elif status == PaymentStatus.FAILED:
            payment.set_canceled(_id, info="failed",
                                 external_id=f"external_{external_id}")
            logger.info(
                f"cancelled payment wtih id {_id} and external id {external_id} because failed")

        elif status == PaymentStatus.EXPIRED:
            payment.set_canceled(_id, info="expired",
                                 external_id=f"external_{external_id}")
            logger.info(
                f"cancelled payment wtih id {_id} and external id {external_id} because expired")

        elif abs((datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") - datetime.today()).days) > 7:
            payment.set_canceled(_id, info="outdated",
                                 external_id=f"external_{external_id}")
            logger.info(
                f"cancelled payment wtih id {_id} and external id {external_id} because outdated")

        elif status in {PaymentStatus.WAITING,
                        PaymentStatus.CONFIRMING,
                        PaymentStatus.CONFIRMED,
                        PaymentStatus.SENDING}:
            logger.info(
                f"in pay payment wtih id {_id} and external id {external_id}")

        else:
            logger.error(
                f"No directions for payment with status \"{status}\", "
                f"invoice id = {external_id}, bill payment id = {_id}"
            )

    def __convert_is_test_to_bool(self, is_test: str = "on") -> bool:
        """Convert BILLmanager paymethod string "is_test" value to a boolean value

        Keyword arguments:
        is_test -- BILLmanager paymethod value equivalent to "is_test"
        """
        return is_test == "on"


if __name__ == "__main__":
    NOWPaymentsModule().run()
