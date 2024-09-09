#!/usr/bin/python3

from decimal import ROUND_CEILING, Decimal
import sys
from string import Template

sys.path.insert(0, "/usr/local/mgr5/lib/python")

from billmgr.modules.paymentcgi import PageType, PaymentCgi, PaymentCgiType, run_cgi
import billmgr.logger as logging


logging.init_logging("cpwidgetrecurring")
logger = logging.get_logger("cpwidgetrecurring")


PAYMENT_FORM_FILE = "etc/paymethods/cloudpayments_widget.html"
FORM_404_FILE = "etc/paymethods/cloudpayments_404.html"

MIN_AMOUNT = 1


class CloudPaymentsRecurringCgi(PaymentCgi):
    def __init__(self):
        # Check for correctly formed cgi-script
        try:
            PaymentCgi.__init__(self)
            logger.info("CGI script initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize CGI script: {str(e)}")
            self.redirect_to_url(FORM_404_FILE)

    def cgi_type(self) -> PaymentCgiType:
        return PaymentCgiType.NewRecurring

    def process(self):
        logger.info("Processing recurring payment CGI request...")

        logger.debug(f"Payment_params: {self.payment_params}")
        logger.debug(f"Paymethod_params: {self.paymethod_params}")
        logger.debug(f"Recurring_params: {self.recurring_params}")
        logger.debug(f"Success page: {self.get_page(PageType.Success)}")
        logger.debug(f"Fail page: {self.get_page(PageType.Fail)}")

        # Collect the necessary data to form the payment widget
        result_cgi = "/mancgi/cpwidgetrecurringresult"
        publickey = self.paymethod_params["publickey"]
        invoiceId = self.elid() + "#" + self.recurring_params["randomnumber"]
        account_id = self.recurring_params["subaccount"]
        currency_iso = self.currency_params["iso"]
        language = self.lang if self.lang else "en"
        description = "Установочный платёж" if language == "ru" else "Set-up payment"

        widget_data = {
            "publicId": publickey,
            "invoiceId": invoiceId,
            "accountId": account_id,
            "amount": MIN_AMOUNT,
            "currency": currency_iso,
            "description": description,
            "retryPayment": 0,  # 0 - not allowed attempts, 1 - allowed attempts
        }
        logger.debug(f"Prepared widget data for recurring payment: {widget_data}")

        # Redirect the user to the payment widget
        with open(PAYMENT_FORM_FILE, "r") as f:
            form = Template(f.read())
            form = form.substitute(
                result_cgi=result_cgi, language=language, widget_data=widget_data
            )
            sys.stdout.write(form)
        logger.info(f"Payment widget form displayed for elid {self.elid()}.")


if __name__ == "__main__":
    run_cgi(CloudPaymentsRecurringCgi)
