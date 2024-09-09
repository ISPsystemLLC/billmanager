#!/usr/bin/python3

from decimal import ROUND_CEILING, Decimal
import sys
from string import Template

sys.path.insert(0, "/usr/local/mgr5/lib/python")

from billmgr.modules.paymentcgi import PageType, PaymentCgi, PaymentCgiType, run_cgi
import billmgr.logger as logging
import billmgr.payment as payment
import billmgr.db as db
import billmgr.misc as misc

import cloudpayments.api as cloudpayments_api

logging.init_logging("cpwidgetpayment")
logger = logging.get_logger("cpwidgetpayment")


PAYMENT_FORM_FILE = "etc/paymethods/cloudpayments_widget.html"
FORM_404_FILE = "etc/paymethods/cloudpayments_404.html"

PAYMETHOD_MODULE_NAME = "pmcloudpaymentswidget"


class CloudPaymentsPaymentCgi(PaymentCgi):
    def __init__(self):
        # Check for correctly formed cgi-script
        try:
            PaymentCgi.__init__(self)
            logger.info("CGI script initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize CGI script: {str(e)}")
            self.redirect_to_url(FORM_404_FILE)

    def cgi_type(self) -> PaymentCgiType:
        return PaymentCgiType.Payment

    def process(self):
        logger.info("Processing payment CGI request...")

        # Cgi-script is formed correctly,
        # check for current payment status
        # before redirecting the user to the payment widget
        invoiceId = self.payment_params["externalid"]
        if invoiceId:
            auth = cloudpayments_api.authenticate(
                cloudpayments_api.AuthData(
                    publickey=self.paymethod_params["publickey"],
                    apisecret=self.paymethod_params["apisecret"],
                )
            )

            response_payment_details = cloudpayments_api.request_check_status(
                auth, invoiceId
            )
            payment_details = cloudpayments_api.parse_payment(response_payment_details)
            logger.debug(f"Payment_details: {payment_details}")

            status_code = payment_details.status_code
            logger.debug(f"Payment status for invoiceId {invoiceId}: {status_code}")
            
            is_store_payment = self.payment_params["store_payment"]

            # Redirect the user to pages according to the current payment status
            if status_code == cloudpayments_api.PaymentStatus.COMPLETED.value:
                if (
                    is_store_payment
                    and payment_details.token is not None
                    and len(payment_details.token) > 0
                ):
                    payment.set_paid(
                        int(self.elid()),
                        invoiceId,
                        payment.RecurringInfo(
                            status=payment.RecurringStatus.rsStored,
                            token=payment_details.token,
                            data1="",
                            data2="",
                            name="",
                        ),
                    )
                    logger.info(
                        f"Stored payment method updated for payment ID: {int(self.elid())}, redirecting to success page."
                    )
                else:
                    payment.set_paid(int(self.elid()), invoiceId)
                    logger.info(f"Payment completed for payment ID: {int(self.elid())}, redirecting to success page.")
                        
                self.redirect_to_url(
                    f"{self.get_page(PageType.Success)}&elid={self.elid()}&module={PAYMETHOD_MODULE_NAME}"
                )
                return
            elif (status_code == cloudpayments_api.PaymentStatus.CANCELLED.value) or (
                status_code == cloudpayments_api.PaymentStatus.DECLINED.value
            ):
                payment.set_canceled(int(self.elid()), invoiceId)

                if is_store_payment:
                    id_recurring = db.get_first_record_unwrap(
                        "SELECT id FROM recurring"
                        f" WHERE init_payment={int(self.elid())}"
                    ).as_int("id")
                    
                    misc.MgrctlXml('stored_paymethod.save_failed', elid=id_recurring)
                    logger.info(
                        f"Stored payment method updated for payment ID: {int(self.elid())}."
                    )
                    
                logger.warning(
                    f"Payment declined or cancelled or expired for payment ID: {int(self.elid())}, redirecting to fail page."
                )

                self.redirect_to_url(
                    f"{self.get_page(PageType.Fail)}&elid={self.elid()}&module={PAYMETHOD_MODULE_NAME}"
                )
                return
            elif (
                status_code
                == cloudpayments_api.PaymentStatus.AWAITING_AUTHENTICATION.value
            ):
                self.redirect_to_url(
                    f"{self.get_page(PageType.Pending)}&elid={self.elid()}&module={PAYMETHOD_MODULE_NAME}"
                )
                logger.info(
                    f"Payment awaiting authentication for elid {self.elid()}, redirecting to pending page."
                )
                return
            elif status_code == None:
                # The payment is missing in CP
                pass
            else:
                self.redirect_to_url(FORM_404_FILE)
                logger.error(
                    f"Unexpected status code {status_code} for payment with invoiceId: {invoiceId}"
                )
                return

        logger.debug(f"Payment_params: {self.payment_params}")
        logger.debug(f"Paymethod_params: {self.paymethod_params}")
        logger.debug(f"Success page: {self.get_page(PageType.Success)}")
        logger.debug(f"Fail page: {self.get_page(PageType.Fail)}")
        logger.debug(f"Pending page: {self.get_page(PageType.Pending)}")

        # Collect the necessary data to form the payment widget
        result_cgi = "/mancgi/cpwidgetresult"
        publickey = self.paymethod_params["publickey"]
        invoiceId = self.elid() + "#" + self.payment_params["randomnumber"]
        account_id = self.payment_params["subaccount"]
        amount = Decimal(self.payment_params["paymethodamount"]).quantize(
            Decimal("0.01"), ROUND_CEILING
        )
        amount = float(amount)
        currency_iso = self.currency_params["iso"]
        description = self.payment_params["description"]
        language = self.lang if self.lang else "en"

        widget_data = {
            "publicId": publickey,
            "invoiceId": invoiceId,
            "accountId": account_id,
            "amount": amount,
            "currency": currency_iso,
            "description": description,
            "retryPayment": 0,  # 0 - not allowed attempts, 1 - allowed attempts
        }
        logger.debug(f"Prepared widget data for payment: {widget_data}")

        # Redirect the user to the payment widget
        with open(PAYMENT_FORM_FILE, "r") as f:
            form = Template(f.read())
            form = form.substitute(
                result_cgi=result_cgi, language=language, widget_data=widget_data
            )
            sys.stdout.write(form)
        logger.info(f"Payment widget form displayed for elid {self.elid()}.")

        payment.set_in_pay(int(self.elid()), invoiceId)


if __name__ == "__main__":
    run_cgi(CloudPaymentsPaymentCgi)
