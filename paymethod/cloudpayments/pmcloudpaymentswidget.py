#!/usr/bin/env python3

import argparse
import datetime as dt
import xml.etree.ElementTree as ET
import sys

sys.path.insert(0, "/usr/local/mgr5/lib/python")

from billmgr.modules.paymethod import (
    PaymethodModule,
    Feature,
    Param,
    RecurringType,
    recurring_type_param,
)
import billmgr.db as db
import billmgr.exception as exc
import billmgr.misc as misc
import billmgr.logger as logging
import billmgr.payment as payment
import billmgr.session as session

import cloudpayments.api as cloudpayments_api

logging.init_logging("pmcloudpaymentswidget")
logger = logging.get_logger("pmcloudpaymentswidget")


PAYMETHOD_MODULE_NAME = "pmcloudpaymentswidget"


class CloudPaymentsWidget(PaymethodModule):
    def __init__(self) -> None:
        super().__init__()
        self.set_description("CloudPayments Widget Integration")

        self._add_feature(Feature.REDIRECT)
        self._add_feature(Feature.NOT_PROFILE)

        self._add_callable_feature(Feature.PMVALIDATE, self.pm_validate)

        self._add_feature(Feature.REFUND)
        self._add_callable_feature(Feature.RFSET, self.rf_set)

        self._add_feature(Feature.RP_SUCCESS)
        self._add_feature(Feature.RP_FAIL)

        self._add_feature(Feature.RECURRING)
        self._add_feature(Feature.STORED)
        self._add_callable_feature(Feature.RCPAY, self.rc_pay)

        self._add_callable_feature(Feature.CHECKPAY, self.checkpay)

        self._add_param(Param.PAYMENT_SCRIPT, "/mancgi/cpwidgetpayment")
        self._add_param(Param.RECURRING_SCRIPT, "/mancgi/cpwidgetrecurring")
        self._add_param(
            Param.RECURRING_TYPE,
            recurring_type_param([RecurringType.rtMaxAmount, RecurringType.rtRedirect]),
        )

    def _on_raise_exception(self, args: argparse.Namespace, err: exc.XmlException):
        print(err.as_xml())

    def pm_validate(self):
        xml = session.get_input_xml()

        publickey = xml.findtext("publickey", default="")
        apisecret = xml.findtext("apisecret", default="")
        logger.debug(f"Validating payment method with publickey: {publickey}")

        # Checks for a valid public key, api secret
        cloudpayments_api.authenticate(cloudpayments_api.AuthData(publickey, apisecret))

        paymethod_id = xml.findtext("paymethod/id", default="")
        paymethod_currency = xml.findtext("paymethod/currency", default="")

        # Checks for currency
        if paymethod_id:
            currency_iso = misc.get_currency_data(int(paymethod_currency)).iso
            logger.debug(f"Currency for validation: {currency_iso}")
            if currency_iso not in cloudpayments_api.SUPPORTED_CURRENCIES:
                logger.error(f"Unsupported currency: {currency_iso}")
                exception = exc.XmlException("unsupported_currency")
                exception.add_param(
                    "currencies", ", ".join(cloudpayments_api.SUPPORTED_CURRENCIES)
                )
                raise exception

    def rf_set(self):
        xml = session.get_input_xml()
        logger.debug(f'Incoming XML for refund: {ET.tostring(xml, encoding="utf8")}')

        payment_id = int(xml.findtext("source_payment", default=""))
        logger.debug(f"Processing refund for payment ID: {payment_id}")

        payment_params = self.get_payment_params(payment_id)
        method_params = self.get_method_params(int(payment_params["paymethod"]))

        external_id = payment_params["externalid"]

        # Retrieve the payment amount
        paymethod_refund_amount = cloudpayments_api.amount_from_str(
            xml.findtext("payment_paymethodamount", default="")
        )
        paymethod_refund_amount = abs(paymethod_refund_amount)
        logger.debug(f"Refund amount: {paymethod_refund_amount}")

        publickey = method_params["publickey"]
        apisecret = method_params["apisecret"]

        auth = cloudpayments_api.authenticate(
            cloudpayments_api.AuthData(publickey, apisecret)
        )

        # Get the original transaction to be refunded in full or in part
        response_payment_details = cloudpayments_api.request_check_status(
            auth, external_id
        )
        payment_details = cloudpayments_api.parse_payment(response_payment_details)

        transaction_id = payment_details.original_transaction_id
        if transaction_id == None:
            transaction_id = payment_details.transaction_id
        logger.debug(f"Transaction ID for refund: {transaction_id}")

        # The full or partial refund is made through the original transaction
        response_refund_details = cloudpayments_api.request_refund_payment(
            auth, transaction_id, paymethod_refund_amount
        )
        refund_details = cloudpayments_api.parse_refund(response_refund_details)
        logger.debug(f"Refund_details: {refund_details}")

        if refund_details.success:
            logger.info(f"Refund successful for transaction ID: {transaction_id}")
        else:
            logger.error(
                f"Refund failed for transaction ID: {transaction_id}, response: {refund_details.message}"
            )
            raise cloudpayments_api.RefundStatusFailedError(refund_details.message)

    def rc_pay(self, payment_id: int):
        payment_params = self.get_payment_params(payment_id)
        method_params = self.get_method_params(int(payment_params["paymethod"]))
        recurring_params = self.get_recurring_params(int(payment_params["recurring"]))

        logger.debug(f"Initiating recurring payment for payment ID: {payment_id}")
        logger.debug(f"Payment_params : {payment_params}")
        logger.debug(f"Method_params : {method_params}")
        logger.debug(f"Recurring_params : {recurring_params}")

        try:
            # Retrieve the payment amount
            currency = misc.get_currency_data(int(payment_params["currency"])).iso
            paymethod_recurring_amount = cloudpayments_api.amount_from_str(
                payment_params["amount"]
            )

            # Get autopayment data
            autopayment = db.get_first_record(
                f"""
                SELECT p.id, p.recurring, r.token, p.paymethodamount, p.randomnumber, p.currency, p.subaccount, pm.xmlparams 
                FROM payment p
                JOIN paymethod pm ON p.paymethod = pm.id
                JOIN recurring r ON p.recurring = r.id
                WHERE module = '{PAYMETHOD_MODULE_NAME}' AND
                p.id = {payment_id};
            """
            )

            if autopayment is None:
                logger.error(f"Autopayment not found for payment ID: {payment_id}")
                raise exc.XmlException("missed_autopayment")

            publickey = method_params["publickey"]
            apisecret = method_params["apisecret"]

            auth = cloudpayments_api.authenticate(
                cloudpayments_api.AuthData(publickey, apisecret)
            )

            external_id = (
                f"{autopayment.as_str('id')}#{autopayment.as_str('randomnumber')}"
            )
            logger.debug(f"External ID for recurring payment: {external_id}")

            # Executing a token payment request
            response_recurring_details = cloudpayments_api.request_recurring_payment(
                auth=auth,
                amount=paymethod_recurring_amount,
                currency=currency,
                accountId=autopayment.as_str("subaccount"),
                Token=recurring_params["token"],
                InvoiceId=external_id,
            )

            recurring_details = cloudpayments_api.parse_payment(
                response_recurring_details
            )
            logger.debug(f"Recurring payment details: {recurring_details}")

            # Change status of payment
            if (
                recurring_details.status_code
                != cloudpayments_api.PaymentStatus.COMPLETED.value
            ):
                reason = recurring_details.message
                logger.error(f"Recurring payment failed, reason: {reason}")

                payment.set_canceled(payment_id, external_id)
                raise cloudpayments_api.RecurringStatusFailedError(reason)

            payment.set_paid(payment_id, external_id)
            logger.info(f"Recurring payment successful for payment ID: {payment_id}")

        except Exception as e:
            logger.error(
                f"Error processing recurring payment for payment ID: {payment_id}"
            )
            payment.set_canceled(payment_id, "")
            raise e

    def checkpay(self):
        with misc.FileLock(
            f"var/run/lock/{PAYMETHOD_MODULE_NAME}_{Feature.CHECKPAY}"
        ) as _:
            self.checkpay_no_lock()

    def checkpay_no_lock(self):
        logger.info(f"Starting checkpay process")

        from_date = dt.datetime.today() - dt.timedelta(days = 7)
        
        # Get all the payments that are inpay in the last 7 days
        records = db.db_query(
            " SELECT p.id, p.externalid, p.xmlparams AS payment_xmlparams, pm.xmlparams AS paymethod_xmlparams,"
            " p.createdate as payment_createdate"
            " FROM payment p"
            " JOIN paymethod pm ON pm.id = p.paymethod"
            f' WHERE module = "{PAYMETHOD_MODULE_NAME}"'
            f' AND p.status = {payment.PaymentStatus.psInPay.value}'
            f' AND p.createdate >= \'{from_date.strftime("%Y-%m-%d")}\''
        )

        for rec in records:
            paymethod_xmlparams = ET.fromstring(rec.as_str("paymethod_xmlparams"))

            auth = cloudpayments_api.authenticate(
                cloudpayments_api.AuthData(
                    paymethod_xmlparams.findtext("publickey", default=""),
                    paymethod_xmlparams.findtext("apisecret", default=""),
                )
            )

            payment_id = rec.as_int("id")
            external_id = rec.as_str("externalid")
            logger.debug(
                f"Checking payment status for payment ID: {payment_id}, External ID: {external_id}"
            )

            try:
                payment_xmlparams = ET.fromstring(rec.as_str("payment_xmlparams"))
                logger.debug(f"Payment XML params: {payment_xmlparams}")

                is_store_payment = (
                    payment_xmlparams.findtext("store_payment", default="") == "on"
                )
                
                # if is_expired==True, then cancel payment that are more than a day in pay
                # and delete the customized stored payment method
                difference = dt.datetime.today() - dt.datetime.strptime(rec.as_str("payment_createdate"), "%Y-%m-%d %H:%M:%S")
                is_expired = difference >= dt.timedelta(days=1)

                # Get payment details
                response_payment_details = cloudpayments_api.request_check_status(
                    auth, external_id
                )
                
                payment_details = cloudpayments_api.parse_payment(
                    response_payment_details
                )
                logger.info(f"Payment_details: {payment_details}")

                if (
                    payment_details.message == "Not found"
                ):  # the payment was initiated by billmgr, but it has not appeared in CP yet
                    logger.debug(
                        f"Payment ID: {payment_id}, External ID: {external_id} is still in pay. CP message: {payment_details.message}"
                    )

                status_code = payment_details.status_code
                logger.debug(
                    f"Payment status for invoiceId {external_id}: {status_code}"
                )

                # Payment is processed according to the payment status
                if status_code == cloudpayments_api.PaymentStatus.COMPLETED.value:
                    if (
                        is_store_payment
                        and payment_details.token is not None
                        and len(payment_details.token) > 0
                    ):
                        payment.set_paid(
                            payment_id,
                            external_id,
                            payment.RecurringInfo(
                                status=payment.RecurringStatus.rsStored,
                                token=payment_details.token,
                                data1="",
                                data2="",
                                name="",
                            ),
                        )
                        logger.info(
                            f"Stored payment method updated for payment ID: {payment_id}"
                        )
                    else:
                        payment.set_paid(payment_id, external_id)
                        logger.info(f"Payment completed for payment ID: {payment_id}")

                elif (
                    status_code == cloudpayments_api.PaymentStatus.DECLINED.value
                    or status_code == cloudpayments_api.PaymentStatus.CANCELLED.value
                    or is_expired
                ):
                    logger.warning(
                        f"Payment declined or cancelled or expired for payment ID: {payment_id}, External ID: {external_id}"
                    )
                    payment.set_canceled(payment_id, external_id)

                    if is_store_payment:
                        id_recurring = db.get_first_record_unwrap(
                            "SELECT id FROM recurring"
                            f" WHERE init_payment={payment_id}"
                        ).as_int("id")
                        
                        misc.MgrctlXml('stored_paymethod.save_failed', elid=id_recurring)

                elif ( 
                    status_code == cloudpayments_api.PaymentStatus.AWAITING_AUTHENTICATION.value 
                ): 
                    logger.info( 
                        f"Payment ID: {payment_id}, External ID: {external_id} is still in pay. CP payment status: {status_code}" 
                    ) 
                    continue
            except:
                logger.error(
                    f"Error when processing payment ID: {payment_id}, External ID: {external_id}"
                )


if __name__ == "__main__":
    CloudPaymentsWidget().run()
