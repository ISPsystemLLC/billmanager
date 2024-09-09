#!/usr/bin/python3

import sys

sys.path.insert(0, "/usr/local/mgr5/lib/python")

from billmgr.modules.paymentcgi import PageType, PaymentCgi, PaymentCgiType, run_cgi
import billmgr.logger as logging
import billmgr.payment as payment
import billmgr.db as db
import billmgr.misc as misc

import cloudpayments.api as cloudpayments_api

logging.init_logging("cpwidgetresult")
logger = logging.get_logger("cpwidgetresult")

PAYMETHOD_MODULE_NAME = "pmcloudpaymentswidget"


class CloudPaymentsResultCgi(PaymentCgi):
    def __init__(self):
        self._payment_id = 0
        PaymentCgi.__init__(self)

    def cgi_type(self) -> PaymentCgiType:
        return PaymentCgiType.Payment

    def parse_input(self):
        self._payment_id = self.input["invoiceId"].split("#")[0]
        logger.info(f"Parsed payment ID: {self._payment_id}")

    def elid(self) -> str:
        return str(self._payment_id)

    def _find_recurring(self, payment_id: str) -> str:
        logger.info(
            f"Looking for recurring payment with init_payment ID: {payment_id}"
        )
        recurring_id = db.get_first_record_unwrap(
            f"SELECT id FROM recurring WHERE init_payment={payment_id}"
        ).as_str("id")
        logger.info(f"Found recurring payment ID: {recurring_id}")
        return recurring_id

    def _delete_recurring(self, id: str) -> None:
        logger.info(f"Deleting recurring payment with ID: {id}")
        misc.MgrctlXml('stored_paymethod.save_failed', elid=id)

    def process(self):
        logger.info("Processing payment result CGI request...")

        external_id = self.input["invoiceId"]
        logger.info(f"Received payment with external ID: {external_id}")

        try:
            auth = cloudpayments_api.authenticate(
                cloudpayments_api.AuthData(
                    self.paymethod_params["publickey"],
                    self.paymethod_params["apisecret"],
                )
            )

            # Get payment details
            response_payment_details = cloudpayments_api.request_check_status(
                auth, external_id
            )
            payment_details = cloudpayments_api.parse_payment(response_payment_details)
            logger.info(f"Payment_details: {payment_details}")

            status_code = payment_details.status_code
            logger.info(f"Payment status for invoiceId {external_id}: {status_code}")

            # Here we have 5 statuses:
            # In the CANCELLED and DECLINED statuses, the payment is canceled
            # In the COMPLETED and AUTHORIZED statuses, the payment is completed, but the AUTHORIZED status is present only for two-stage payments
            # The status of the AWAITING_AUTHENTICATION should not be present here
            if status_code == cloudpayments_api.PaymentStatus.COMPLETED.value:
                if payment_details.token is not None and len(payment_details.token) > 0:
                    payment.set_paid(
                        int(self.elid()),
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
                        f"Stored payment method updated for payment ID: {self.elid()}"
                    )
                else:
                    payment.set_paid(int(self.elid()), external_id)
                    logger.info(f"Payment completed for payment ID: {self.elid()}")

                self.redirect_to_url(
                    f"{self.get_page(PageType.Success)}&elid={self.elid()}&module={PAYMETHOD_MODULE_NAME}"
                )

            elif (
                status_code == cloudpayments_api.PaymentStatus.CANCELLED.value
                or status_code == cloudpayments_api.PaymentStatus.DECLINED.value
                or status_code == None      # The payment is missing in CP
            ):
                logger.warning(
                    f"Payment declined or cancelled for payment ID: {self.elid()}, External ID: {external_id}"
                )
                raise Exception(status_code)

        except Exception as e:
            logger.info(f"Exception: is Exception ")
            
            payment.set_canceled(int(self.elid()), external_id)

            if "store_payment" in self.payment_params:
                id_recurring = self._find_recurring(self.elid())
                self._delete_recurring(id_recurring)

            logger.warning(f"Payment wasn't executed: {e}")
            self.redirect_to_url(
                f"{self.get_page(PageType.Fail)}&elid={self.elid()}&module={PAYMETHOD_MODULE_NAME}"
            )


if __name__ == "__main__":
    run_cgi(CloudPaymentsResultCgi)
