#!/usr/bin/python3

import sys

sys.path.insert(0, "/usr/local/mgr5/lib/python")

from billmgr.modules.paymentcgi import PageType, PaymentCgi, PaymentCgiType, run_cgi
import billmgr.logger as logging
import billmgr.payment as payment

import cloudpayments.api as cloudpayments_api


logging.init_logging("cpwidgetrecurringresult")
logger = logging.get_logger("cpwidgetrecurringresult")

PAYMETHOD_MODULE_NAME = "pmcloudpaymentswidget"


class CloudPaymentsRecurringResultCgi(PaymentCgi):
    def __init__(self):
        self._recurring_id = 0
        PaymentCgi.__init__(self)

    def cgi_type(self) -> PaymentCgiType:
        return PaymentCgiType.NewRecurring

    def parse_input(self):
        self._recurring_id = self.input["invoiceId"].split("#")[0]
        logger.debug(f"Parsed recurring ID: {self._recurring_id}")

    def elid(self) -> str:
        return str(self._recurring_id)

    def process(self):
        logger.info("Processing recurring result CGI request...")

        external_id = self.input["invoiceId"]
        logger.debug(f"Received payment with external ID: {external_id}")

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
            logger.debug(f"Payment_details : {payment_details}")

            status_code = payment_details.status_code
            logger.debug(f"Payment status for invoiceId {external_id}: {status_code}")

            if status_code == cloudpayments_api.PaymentStatus.COMPLETED.value:
                # Call error if token is missing
                if payment_details.token == None:
                    logger.error("Token is missing in payment details")
                    raise cloudpayments_api.TokenNotFoundError()

                # Executes refunds of setup payment
                paymethod_refund_amount = payment_details.amount

                transaction_id = payment_details.original_transaction_id
                if transaction_id == None:
                    transaction_id = payment_details.transaction_id
                logger.debug(f"Transaction ID for refund: {transaction_id}")

                response_refund = cloudpayments_api.request_refund_payment(
                    auth, transaction_id, paymethod_refund_amount
                )
                refund_details = cloudpayments_api.parse_refund(response_refund)
                logger.debug(f"Refund_details: {refund_details}")

                # Autopayments and stored payment method are successful
                # if it was formed a token and returned a setup payment
                if refund_details.success:
                    if self.is_stored_paymethod(
                        payment.RecurringStatus(int(self.recurring_params["status"]))
                    ):
                        status = payment.RecurringStatus.rsStored
                    else:
                        status = payment.RecurringStatus.rsActive

                    logger.info("Refund successful, updating recurring payment info")
                    payment.save_recurring_info(
                        int(self.elid()),
                        payment.RecurringInfo(
                            status=status,
                            token=payment_details.token,
                            data1="",
                            data2="",
                            name="",
                        ),
                    )

                    logger.info("Recurring payment info updated successfully")
                    self.redirect_to_url(
                        f"{self.get_page(PageType.Success)}&elid={self.elid()}&module={PAYMETHOD_MODULE_NAME}"
                    )
                    logger.info("Redirecting to success page")
                else:
                    logger.error("Refund failed")
                    raise Exception("refund failed")
            else:
                logger.error(f"Payment failed with status code: {status_code}")
                raise Exception("payment failed")

        except Exception as e:
            if self.is_stored_paymethod(
                payment.RecurringStatus(int(self.recurring_params["status"]))
            ):
                status = payment.RecurringStatus.rsDisabled
            else:
                status = payment.RecurringStatus.rsClosed

            logger.warning(f"Recurring payment failed: {e}")
            payment.save_recurring_info(
                int(self.elid()),
                payment.RecurringInfo(
                    status=status,
                    token="",
                    data1="",
                    data2="",
                    name="",
                ),
            )
            self.redirect_to_url(
                f"{self.get_page(PageType.Fail)}&elid={self.elid()}&module={PAYMETHOD_MODULE_NAME}"
            )
            logger.info("Redirecting to fail page")


if __name__ == "__main__":
    run_cgi(CloudPaymentsRecurringResultCgi)
