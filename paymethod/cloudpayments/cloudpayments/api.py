import decimal
from enum import Enum
import requests
from requests.auth import HTTPBasicAuth
from typing import NamedTuple

import billmgr.logger as logging
from billmgr.exception import XmlException

MODULE = "cloudpayments_api"

logging.init_logging(MODULE)
logger = logging.get_logger(MODULE)

API_URL = "https://api.cloudpayments.ru"
DEFAULT_TIMEOUT = 300  # The timeout for receiving a response from the API is 5 minutes

SUPPORTED_CURRENCIES = [
    "RUB",
    "EUR",
    "USD",
    "GBP",
    "UAH",
    "BYN",
    "KZT",
    "AZN",
    "CHF",
    "CZK",
    "CAD",
    "PLN",
    "SEK",
    "TRY",
    "CNY",
    "INR",
    "BRL",
    "ZAR",
    "UZS",
    "BGN",
    "RON",
    "AUD",
    "HKD",
    "GEL",
    "KGS",
    "AMD",
    "AED",
]


def amount_from_str(amount: str) -> decimal.Decimal:
    return decimal.Decimal(amount).quantize(
        decimal.Decimal("0.01"), decimal.ROUND_CEILING
    )


# _____________________AUTHENTICATION________________________


class AuthData(NamedTuple):
    publickey: str
    apisecret: str


class Auth(NamedTuple):
    url: str
    basic: HTTPBasicAuth


class CloudPaymentsAuthError(XmlException):
    def __init__(self):
        super().__init__("wrong_terminal_info")


def authenticate(auth: AuthData) -> Auth:
    logger.info("api.authenticate run")

    basic = HTTPBasicAuth(auth.publickey, auth.apisecret)
    url = API_URL

    response = requests.request(
        method="POST", url=f"{url}/test", auth=basic, timeout=DEFAULT_TIMEOUT
    )
    logger.debug(f"authenticate => {response}")

    if not response.ok:
        raise CloudPaymentsAuthError()

    return Auth(url, basic)


# _____________________BASIC_REQUESTS________________________


class CloudPaymentsRequestErrorNullResponse(XmlException):
    def __init__(self):
        super().__init__("json_parsing_error_null_response")


class CloudPaymentsRequestError(XmlException):
    def __init__(self, error: str, error_description: str):
        super().__init__("json_parsing_error", "", error)
        super().add_param("description", error_description)


def __request(
    auth: Auth, url: str, http_method: str, data: dict = {}
) -> requests.Response:

    logger.debug(
        f"cloudpayments request basic auth for username '{auth.basic.username}'"
    )
    logger.debug(f"cloudpayments request url = {url}")
    logger.debug(f"cloudpayments request data = {data}")

    response = requests.request(
        method=http_method, url=url, json=data, auth=auth.basic, timeout=DEFAULT_TIMEOUT
    )

    logger.debug(f"cloudpayments response status: {response.status_code}")
    logger.debug(f"cloudpayments response body: {response.text}")

    if not response.ok:
        if not response.text:
            raise CloudPaymentsRequestErrorNullResponse()

        error = response.json()["ErrorCode"]
        error_description = response.json()["Message"]
        raise CloudPaymentsRequestError(error, error_description)

    return response


# ______________________PAYMENT____________________________


class Payment(NamedTuple):
    transaction_id: int = None
    invoice_id: str = None
    amount: decimal.Decimal = None
    original_transaction_id: int = None
    status_code: int = None
    token: str = None
    success: bool = None
    message: str = None


def request_check_status(auth: Auth, cloudpayments_invoice_id: str):
    logger.info("api.request_check_status run")

    data = {"invoiceId": cloudpayments_invoice_id}
    url = f"{auth.url}/v2/payments/find"

    return __request(auth, url, "POST", data=data)


def parse_payment(response: requests.Response) -> Payment:
    logger.info("api.parse_payment run")

    json = response.json()

    success = json["Success"]
    logger.info(f"success = {success}")
    message = json["Message"]
    logger.info(f"message = {message}")

    if "Model" in json:

        json_model = json["Model"]

        logger.info(f"json_model = {json_model}")

        transaction_id = json_model["TransactionId"]
        invoice_id = json_model["InvoiceId"]
        amount = json_model["Amount"]
        original_transaction_id = json_model["OriginalTransactionId"]
        status_code = json_model["StatusCode"]
        token = json_model["Token"]

        return Payment(
            transaction_id,
            invoice_id,
            amount,
            original_transaction_id,
            status_code,
            token,
            success,
            message,
        )

    else:
        return Payment(
            success=success,
            message=message,
        )


# Other statuses https://developers.cloudpayments.ru/#statusy-operatsiy
class PaymentStatus(Enum):
    AWAITING_AUTHENTICATION = 1
    AUTHORIZED = 2
    COMPLETED = 3
    CANCELLED = 4
    DECLINED = 5


class CapturePaymentCancelledError(XmlException):
    def __init__(self):
        super().__init__("capture_payment_cancelled")


class CapturePaymentInvalidStatus(XmlException):
    def __init__(self, status: str):
        super().__init__("capture_payment_invalid_status", "", status)


class CapturePaymentModelNotExist(XmlException):
    def __init__(self, message):
        super().__init__("capture_payment_model_not_exist", "", message)


# ______________________REFUND________________________


class Refund(NamedTuple):
    success: bool
    message: str


class RefundStatusFailedError(XmlException):
    def __init__(self, reason: str):
        super().__init__("refund_failure")
        super().add_param("reason", reason)


def request_refund_payment(
    auth: Auth, transactionId, amount: decimal.Decimal
) -> requests.Response:
    logger.info("api.request_refund_payment run")

    data = {"TransactionId": transactionId, "Amount": abs(float(amount))}
    url = f"{auth.url}/payments/refund"

    return __request(auth, url, "POST", data=data)


def parse_refund(response: requests.Response) -> Refund:
    logger.info("api.parse_refund run")

    json = response.json()

    success = json["Success"]
    message = json["Message"]

    return Refund(success, message)


# ______________________RECURRING________________________


class RecurringStatusFailedError(XmlException):
    def __init__(self, reason: str):
        super().__init__("recurring_failure")
        super().add_param("reason", reason)


def request_recurring_payment(
    auth: Auth, amount: decimal.Decimal, currency, accountId, Token, InvoiceId
) -> requests.Response:
    logger.info("api.request_recurring_payment run")

    data = {
        "Amount": float(amount),
        "Currency": currency,
        "AccountId": accountId,
        "TrInitiatorCode": 0,  # 0 initiated by merchant, 1 - initiated by cardholder
        "PaymentScheduled": 1,  # 0 - not scheduled, 1 - scheduled
        "Token": Token,
        "InvoiceId": InvoiceId,
    }

    # https://developers.cloudpayments.ru/#oplata-po-tokenu-rekarring
    url = f"{auth.url}/payments/tokens/charge"

    return __request(auth, url, "POST", data=data)


class TokenNotFoundError(XmlException):
    def __init__(self):
        super().__init__("token_not_found")
