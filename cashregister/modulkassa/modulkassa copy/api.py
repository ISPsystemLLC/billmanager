"""Interaction with ModulKassa API"""
import decimal
import datetime as dt
from enum import Enum
from typing import NamedTuple, List, Optional, Tuple
import requests
from requests.auth import HTTPBasicAuth

from billmgr.logger import get_logger
from billmgr.exception import XmlException

MODULE = "modulkassa_api"


# _____________________BASIC_REQUESTS________________________


class Auth(NamedTuple):
    """
    Represents the authentication credentials for an HTTP request
    
    """

    url: str
    basic: HTTPBasicAuth


def create_auth_data(url: str, username: str, password: str) -> Auth:
    """
    Creates auth data using HTTPBasicAuth
    
    """

    return Auth(url, HTTPBasicAuth(username, password))


def __request(
    auth: Auth, url: str, http_method: str, data: dict = None
) -> requests.Response:
    """
    Executes an HTTP request using the provided authentication, URL, and method
    
    """

    get_logger(MODULE).debug(f"request: url={url} http_method={http_method} data={data}")

    response = requests.request(
        method=http_method, url=url, json=data, auth=auth.basic, timeout=10
    )

    get_logger(MODULE).debug(f"response: status_code={response.status_code} text={response.text}")

    if not response.ok:
        get_logger(MODULE).error(f"Error with request: {response.text}")

    return response


# ___________________CLASSES____________________


class DocumentStatus(Enum):
    """
    Enum representing statuses of receipt
    
    """

    QUEUED = 1
    PENDING = 2
    PRINTED = 3
    WAIT_FOR_CALLBACK = 4
    COMPLETED = 5
    FAILED = 6
    REQUEUED = 7


class FNStatus(Enum):
    """
    Enum representing the statuses of the fiscalization service.
    
    """

    ASSOCIATED = 1
    READY = 2
    DISABLED = 3
    FAILED = 4


class PaymentMethod(Enum):
    """
    Enum representing diffrent types of payment methods supported by ModulKassa
    
    """
    FULL_PREPAYMENT = 1
    PREPAYMENT = 2
    ADVANCE = 3
    FULL_PAYMENT = 4
    PARTIAL_PAYMENT = 5
    CREDIT = 6
    CREDIT_PAYMENT = 7


class PaymentObject(Enum):
    """
    Enum representing different types of payment objects supported by ModulKassa
    
    """

    COMMODITY = 1
    EXCISE = 2
    JOB = 3
    SERVICE = 4
    GAMBLING_BET = 5
    GAMBLING_PRIZE = 6
    LOTTERY = 7
    LOTTERY_PRIZE = 8
    INTELLECTUAL_ACTIVITY = 9
    PAYMENT = 10
    AGENT_COMMISSION = 11
    COMPOSITE = 12
    ANOTHER = 13



class PaymentType(Enum):
    """
    Enum representing different types of payment methods
    
    """

    CASH = 0
    CARD = 1
    PREPAID = 2
    POSTPAY = 3
    OTHER = 4  # Billmgr keeps it as "provision".
               # Modulkassa only accepts "other".


class VatTag(Enum):
    """
    Enum representing different VAT (Value-Added Tax) tags.
    Supported by ModulKassa
    
    """

    PERCENT_20 = 1102
    PERCENT_10 = 1103
    PERCENT_0 = 1104
    NO_NDS = 1105
    PERCENT_20_120 = 1106
    PERCENT_10_110 = 1107


class DocType(Enum):
    """
    Enum representing different types of receipts.
    
    """

    SALE = 0
    RETURN = 1
    SALE_CORRECTION = 2
    BUY = 3
    BUY_RETURN = 4
    BUY_CORRECTION = 5


class CheckType(Enum):
    """
    Enum representing different types of receipts in fiscalization service.
    
    """

    SALE = 0
    RETURN = 1
    PURCHASE = 2
    RETURN_PURCHASE = 3
    SALE_CORRECTION = 4
    RETURN_CORRECTION = 5
    PURCHASE_CORRECTION = 6
    RETURN_PURCHASE_CORRECTION = 7


class InventPosition(NamedTuple):
    """
    Represents an item in a document, such as a product or service.
    
    """

    name: str
    price: decimal.Decimal
    quantity: int
    vatTag: VatTag
    vatSum: decimal.Decimal
    paymentMethod: PaymentMethod
    paymentObject: PaymentObject


class MoneyPosition(NamedTuple):
    """
    Represents a payment entry in a document.
    
    """

    paymentType: PaymentType
    sum: decimal.Decimal


class Document(NamedTuple):
    """
    Represents the details of a receipt or invoice document.
    
    Attributes:
    id (str): Unique identifier for the document (receipt).
    docNum (str): Document number (unique transaction number).
    docType (DocType): Type of the document (SALE, RETURN, etc.).
    checkoutDateTime (str): The date and time of the transaction in ISO format.
    email (str): The email address associated with the transaction.
    inventPositions (List[InventPosition]): A list of items included in the document.
    moneyPositions (List[MoneyPosition]): A list of payments made.
    """

    id: str
    docNum: str
    docType: DocType
    checkoutDateTime: str
    email: str
    inventPositions: List
    moneyPositions: List


class FiscalInfo(NamedTuple):
    """
    Represents fiscal information related to a receipt.
    
    Attributes:
        shiftNumber: The shift number during which the receipt was issued.
        checkNumber: The receipt number or check number.
        kktNumber: The KKT (cash register terminal) number.
        fnNumber: The fiscal number assigned to the receipt.
        fnDocNumber: The fiscal document number.
        fnDocMark: A unique mark that indicates the document type.
        receiptdate: Document timestamp.
        receiptdate_tz: Timezone offset in ±HH:MM format.
        sumDoc: The total amount of the fiscal document (receipt).
        checkType: The type of the fiscal check (e.g., SALE, RETURN).
        qr: A QR code for validation.
    """
    shiftNumber: Optional[int] = None
    checkNumber: Optional[int] = None
    kktNumber: Optional[str] = None
    fnNumber: Optional[str] = None
    fnDocNumber: Optional[int] = None
    fnDocMark: Optional[int] = None
    receiptdate: Optional[str] = None
    receiptdate_tz: Optional[str] = None
    sumDoc: Optional[decimal.Decimal] = None
    checkType: Optional[CheckType] = None
    qr: Optional[str] = None


class FailureType(Enum):
    """
    Enum represents possible failure types related to fiscalization.

    """

    FN_MEMORY_OVERFLOW = 1
    FN_EXPIRED = 2
    FN_GENERIC_FAILURE = 3
    NON_FN_FAILURE = 4


class FailureInfo(NamedTuple):
    """
    Represents a failure with message related to the fiscalization process of a document.
    
    """

    failure_type: Optional[FailureType] = None
    message: Optional[str] = None


class DocumentDetails(NamedTuple):
    """
    Contains detailed information about the fiscalization status of a receipt or document.
    
    """

    status: Optional[str] = None
    fnState: Optional[FNStatus] = None
    fiscalInfo: Optional[FiscalInfo] = None
    failureInfo: Optional[FailureInfo] = None
    message: Optional[str] = None


# ______________________ASSOCIATE__________________________


def request_associate(auth: Auth, retailpointid) -> requests.Response:
    """
    Creates authorization data for sending receipts for fiscalization via POST request.
    
    """

    get_logger(MODULE).info("request_associate: run")
    get_logger(MODULE).info(f"request_associate input: retailpointid = {retailpointid}")

    url = f"{auth.url}/v1/associate/{retailpointid}"

    return __request(auth, url, "POST")


# ______________________STATUS_FN__________________________


def request_status_fn(auth: Auth) -> requests.Response:
    """
    Requests the fiscalization service status to check its readiness.
    
    """

    get_logger(MODULE).info("request_status: run")

    url = f"{auth.url}/v1/status"

    return __request(auth, url, "GET")


# ______________________SEND_RECEIPT_TO_EXTERNAL_SYSTEM__________________________


def send_receipt_to_external_system(
    auth: Auth, document: Document
) -> requests.Response:
    """
    Gets Document from cashregister and serializes to JSON.
    Sends JSON payload via POST request to Modulkassa.
    
    """

    get_logger(MODULE).info("send_receipt_to_external_system: run")
    get_logger(MODULE).info(f"send_receipt_to_external_system input: document = {document}")

    data = document._asdict()

    url = f"{auth.url}/v2/doc"

    return __request(auth, url, "POST", data)


# ______________________GET_RECEIPT_FROM_EXTERNAL_SYSTEM__________________________


def get_receipt_from_external_system(auth: Auth, external_id: str) -> requests.Response:
    """
    Retrieves the status of a receipt from an external system.
    
    """

    get_logger(MODULE).info("get_receipt_from_external_system: run")
    get_logger(MODULE).info(f"get_receipt_from_external_system input: external_id = {external_id}")

    url = f"{auth.url}/v1/doc/{external_id}/status"

    return __request(auth, url, "GET")


def parse_date(date_str: str) -> Tuple[Optional[dt.datetime], Optional[str]]:
    """
    Parses ISO 8601 date string into datetime object and timezone offset.
    
    Supports multiple formats:
    - With milliseconds and 'Z' (UTC): "2025-05-03T07:29:34.123Z" → (datetime, "+00:00")
    - With ±HH:MM offset:             "2025-05-03T07:29:34+03:00" → (datetime, "+03:00")
    - With ±HHMM offset:              "2025-05-03T07:29:34+0300" → (datetime, "+03:00")
    - Without timezone:               "2025-05-03T07:29:34" → (datetime, None)
    - Invalid format:                 "invalid" → (None, None)
    """
    if not date_str:
        return None, None

    try:
        # Handle UTC 'Z' format
        if date_str.endswith('Z'):
            if '.' in date_str:  # With milliseconds
                dt_obj = dt.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            else:  # Without milliseconds
                dt_obj = dt.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S"), "+00:00"

        # Handle offset formats
        if '+' in date_str or '-' in date_str:
            if 'T' in date_str:
                tz_index = max(date_str.rfind('+'), date_str.rfind('-'))
                if tz_index > date_str.find('T'):
                    dt_part = date_str[:tz_index]
                    tz_part = date_str[tz_index:]

                    # Normalize timezone
                    if ':' in tz_part:
                        tz_offset = tz_part
                    else:
                        tz_offset = f"{tz_part[:3]}:{tz_part[3:]}" if len(tz_part) > 3 else "+00:00"

                    dt_obj = dt.datetime.fromisoformat(dt_part + tz_offset)
                    return dt_obj.strftime("%Y-%m-%d %H:%M:%S"), tz_offset

        # Handle basic ISO format without timezone
        dt_obj = dt.datetime.fromisoformat(date_str)
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S"), None

    except ValueError:
        try:
            # Fallback for non-standard formats
            dt_obj = dt.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            tz_offset = dt_obj.strftime("%z")
            tz_offset = f"{tz_offset[:3]}:{tz_offset[3:]}" if tz_offset else None
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S"), tz_offset
        except ValueError:
            return None, None

def parse_document_details(response: requests.Response) -> DocumentDetails:
    """
    Parses the response from an external system to extract and structure document details.
    
    """

    get_logger(MODULE).info("api.DocumentDetails run")

    json_data = response.json()

    status = json_data.get("status")
    get_logger(MODULE).info(f"status = {status}")

    message = json_data.get("message")
    get_logger(MODULE).info(f"message = {message}")

    fnstate = json_data.get("fnState")

    # Parsing fiscalInfo if it exists
    fiscal_info = FiscalInfo()
    if "fiscalInfo" in json_data and json_data["fiscalInfo"] is not None:
        fiscal_data = json_data["fiscalInfo"]
        try:
            date_str = fiscal_data.get("date")
            get_logger(MODULE).warning("beep1")
            receiptdate, receiptdate_tz = parse_date(date_str)
            get_logger(MODULE).warning("beep2")
            fiscal_info = FiscalInfo(
                shiftNumber=fiscal_data.get("shiftNumber"),
                checkNumber=fiscal_data.get("checkNumber"),
                kktNumber=fiscal_data.get("kktNumber"),
                fnNumber=fiscal_data.get("fnNumber"),
                fnDocNumber=fiscal_data.get("fnDocNumber"),
                fnDocMark=fiscal_data.get("fnDocMark"),
                receiptdate=receiptdate,
                receiptdate_tz=receiptdate_tz,
                sumDoc=decimal.Decimal(fiscal_data.get("sum")) if fiscal_data.get("sum") else None,
                checkType=fiscal_data.get("checkType"),
                qr=fiscal_data.get("qr"),
            )
            get_logger(MODULE).warning("beep3")
        except (ValueError, KeyError) as e:
            get_logger.error(f"Error parsing fiscalInfo: {e}")
            fiscal_info = FiscalInfo()

    # Parsing failureInfo if it exists
    failure_info = FailureInfo()
    if "failureInfo" in json_data and json_data["failureInfo"] is not None:
        fail_data = json_data["failureInfo"]
        failure_info = FailureInfo(
            failure_type=fail_data.get("type"),
            message=fail_data.get("message"),
        )
    get_logger(MODULE).warning("beep4")
    return DocumentDetails(
        status=status,
        fnState=fnstate,
        fiscalInfo=fiscal_info,
        failureInfo=failure_info,
        message=message,
    )


# ______________________EXCEPTIONS_CLASSES__________________________


class UnknownError(XmlException):
    """
    Class representing an unknown error
    
    """

    def __init__(self):
        super().__init__("unknown_error")


class FailedAssociate(XmlException):
    """
    Class representing an error due to failed response via associate request
    
    """

    def __init__(self, reason: str):
        super().__init__("failed_associate")
        super().add_param("reason", reason)


class ServiceUnavailable(XmlException):
    """
    Class representing an error due to failed response via service status request
    
    """

    def __init__(self, reason: str):
        super().__init__("service_unavailable")
        super().add_param("reason", reason)
