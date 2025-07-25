#!/usr/bin/env python3

from typing import Optional, List
import sys
import datetime as dt
import uuid
import hashlib
import time
import requests

sys.path.insert(0, "/usr/local/mgr5/lib/python")

from billmgr.modules.cashregister import CashregisterModule, Feature, ReceiptStatus
from billmgr import db
from billmgr import misc
from billmgr import session
import billmgr.logger as logging
import billmgr.exception as exc
import billmgr.config as conf

import modulkassa.api as modulkassa_api

MODULE = "crmodulkassa"

logging.init_logging(MODULE)
logger = logging.get_logger(MODULE)


# pylint: disable=too-many-instance-attributes
class ModulkassaRegister(CashregisterModule):
    """
    Class representing Modulkassa cashregister

    """

    def __init__(self) -> None:
        super().__init__()
        self.set_description("Modulkassa cash register written on python")

        self._add_callable_feature(Feature.CHECK_CONNECTION, self.check_connection)
        self._add_callable_feature(Feature.SEND_RECEIPT, self.send_receipts)
        self._add_callable_feature(Feature.PREPARED_RECEIPT, self.prepared_receipts)
        self._add_callable_feature(Feature.CHECK_RECEIPT, self.check_receipts)
        self._add_feature(Feature.EXPENSE_RECEIPT)
        self._add_feature(Feature.REFUND_RECEIPT)
        self._add_feature(Feature.MANUAL_MONTHLY_SEND)

        # required fields for integration: username, password, url, retailpointid
        self._username: str = ""
        self._password: str = ""
        self._url: str = ""
        self._retailpointid: str = ""
        self._payment_receipt_description: str = ""
        self._expense_receipt: bool = False
        self._convert_invalid_rate_to_none_rate: bool = False
        self._manual_monthly_send: bool = False

        # fields that got from associate to perform other http request
        self.api_username: str = ""
        self.api_password: str = ""
        self.api_auth: modulkassa_api.Auth = modulkassa_api.Auth("", "")


    def __init_cashregister(self, cash_register: int) -> None:
        logger.info(
            f"__init_cashregister is running: cash_register={cash_register}"
        )

        # Retrive required params for connection
        params = misc.Mgrctl("payment_cash_register.edit", elid=cash_register)

        self._username = str(params['model']['username'])
        self._password = str(params['model']['password'])
        self._url = str(params['model']['url'])
        self._retailpointid = str(params['model']['retailpointid'])
        self._payment_receipt_description = str(params['model']['payment_receipt_description'])
        self._expense_receipt = params['model']['expense_receipt'] == 'on'
        self._convert_invalid_rate_to_none_rate = (
            params['model']['convert_invalid_rate_to_none_rate'] == 'on'
        )
        self._manual_monthly_send = params['model']['manual_monthly_send'] == 'on'


    def __mask_data(self, data: str) -> str:
        """
        Creates a mask for the password or username
        
        """

        masked_data = data[:4] + '*' * (len(data) - 4)

        return masked_data


    def __sanitize_string(self, input_string: str) -> str:
        """
        Sanitizes a string by checking for invalid characters that cannot be used in UNIX file paths
        String is hashed if invalid characters are found
        
        """

        invalid_chars = set("&;|*?'\"`[]()$<>{}^#\\/%!")

        if any(char in invalid_chars for char in input_string):
            hashed = hashlib.sha256(input_string.encode()).hexdigest()
            return hashed
        return input_string


    def __apply_server_tz(self, naive_dt: dt.datetime) -> dt.datetime:
        """
        Applies server's local timezone to a naive datetime object
        
        """

        timestamp = time.mktime(naive_dt.timetuple())
        localtime = time.localtime(timestamp)
        utc_offset = localtime.tm_gmtoff

        return naive_dt.replace(tzinfo=dt.timezone(dt.timedelta(seconds=utc_offset)))


    def __authorize_cashregister(
        self, url: str, username: str, password: str, retailpointid: str
    ) -> requests.Response:
        """
        Authorizes the cash register in the ModulKassa system and checks its availability.
        
        """

        logger.info(
            f"__AUTHORIZE_CASHREGISTER IS RUNNING: "
            f"url={url}, username={self.__mask_data(username)}, "
            f"password={self.__mask_data(password)}, "
            f"retailpointid={retailpointid}"
        )


        # Creating auth data for post reciept to fiscalization for retail point
        auth = modulkassa_api.create_auth_data(url, username, password)

        response_associate = modulkassa_api.request_associate(
            auth=auth, retailpointid=retailpointid
        )

        if not response_associate.ok:
            logger.warning(
                f"__authorize_cashregister: "
                f"Associate is not completed: {response_associate.status_code}"
            )

            raise modulkassa_api.FailedAssociate(response_associate.reason)

        json_associate = response_associate.json()
        self.api_username = json_associate["userName"]
        self.api_password = json_associate["password"]
        self.api_auth = modulkassa_api.create_auth_data(url, self.api_username, self.api_password)

        response_status = modulkassa_api.request_status_fn(auth=self.api_auth)
        if not response_status.ok:
            logger.warning(
                f"__authorize_cashregister: "
                f"Fiscalization service is not ok: {response_status.status_code}"
            )

            raise modulkassa_api.ServiceUnavailable(response_status.reason)

        return response_status


    def __check_service_status(self) -> bool:
        """
        Check fiscalization service's status
        
        """

        response_status = self.__authorize_cashregister(
            self._url,
            self._username,
            self._password,
            self._retailpointid
        )

        json_status = response_status.json()
        logger.info(f"Json_status={json_status}")

        status_fn = json_status["status"]
        logger.info(f"Fiscalization service's status={status_fn}")

        # ! On test mode with api: https://my.modulkassa.ru/api/fn
        # status_fn is always ASSOCIATED
        if status_fn in (
            modulkassa_api.FNStatus.ASSOCIATED.name,
            modulkassa_api.FNStatus.DISABLED.name
            ):
            logger.warning(
                f"Service is not available {status_fn}"
            )
            return False

        return True


    def __get_receipt_from_billmgr(
        self, cash_register: int, status: ReceiptStatus
    ) -> Optional[db.Record]:
        """
        Get receipts from database with exact status
        
        """

        logger.info("__GET_RECEIPT_FROM_BILLMGR IS RUNNING")

        from_date = dt.datetime.today() - dt.timedelta(days=7)

        # Retrive neccessary data about reciept
        result = db.db_query(
            "SELECT pr.id"
            ", pr.payment"
            ", pr.payment_cash_register"
            ", pr.createdate"
            ", pr.receiptdate"
            ", pr.receiptdate_tz"
            ", pr.senddate"
            ", pr.receipt_type"
            ", pr.status"
            ", pr.error_message"
            ", pr.amount"
            ", pr.currency"
            ", pr.fn_number"
            ", pr.fiscal_document_number"
            ", pr.fiscal_document_attribute"
            ", pr.email"
            ", pr.phone"
            ", pr.internalid"
            ", pr.externalid"
            ", pr.disable_change_expense"
            ", pr.is_expense"
            ", pr.subaccount"
            ", pr.last_notify_time"
            ", pr.ofd_receipt_url"
            ", pr.payment_type"
            ", CASE"
            " WHEN COALESCE(pr.internalid, '') = '' THEN pr.id" 
            " ELSE pr.internalid" 
            " END AS external_id"
            ", prj.billurl"
            ", p.billorder"
            ", p.paymethod"
            ", p.id AS payment_id"
            ", p.description AS payment_description"
            " FROM payment_receipt pr"
            " LEFT JOIN payment p ON p.id = pr.payment"
            " LEFT JOIN subaccount sa ON sa.id = COALESCE(p.subaccount, pr.subaccount)"
            " LEFT JOIN project prj ON prj.id = sa.project"
            " WHERE pr.payment_cash_register = %s"
            " AND pr.status = %s"
            " AND pr.createdate >= %s",
            cash_register, status.value, from_date.strftime('%Y-%m-%d')
        )

        logger.info(f"__get_receipt_from_billmgr: db_query result={result}")
        return result


    def is_receipt_expense(self, receipt_id: int) -> bool:
        """
        Returns True if receipt's is_expense flag is 'on', otherwise False
        
        """

        result = db.get_first_record(
            "SELECT is_expense FROM payment_receipt WHERE id = %s",
            receipt_id
        )

        if not result or "is_expense" not in result:
            raise RuntimeError(f"Не удалось получить флаг is_expense для чека id={receipt_id}")

        return result["is_expense"] == 'on'


    def __get_receipt_item_from_billmgr(
        self, payment_receipt: int
    ) -> Optional[db.Record]:
        """
        Get receipt's positions from billmgr database
        
        """

        logger.info(
            f"__GET_RECEIPT_ITEM_FROM_BILLMGR IS RUNNING: "
            f"payment_receipt={payment_receipt}"
        )

        # Retrive neccessary data about reciept
        result = db.db_query(
            "SELECT pri.name"
            ", pri.price"
            ", pri.quantity"
            ", pri.amount AS item_amount"
            ", pri.taxrate"
            ", pri.taxamount"
            ", pri.payment_method"
            ", pri.payment_object"
            ", pri.expense"
            " FROM payment_receipt_item pri"
            " WHERE pri.payment_receipt = %s",
            payment_receipt
        )

        logger.info(f"__get_receipt_item_from_billmgr: db_query result={result}")
        return result


    def __resolve_payment_method(self, receipt: db.Record, receipt_item: db.Record) -> str:
        """
        Determines the payment method.
        
        """

        logger.info("__RESOLVE_PAYMENT_METHOD IS RUNNING")

        payment_method = conf.get_param("ReceiptDefaultPaymentMethod")

        if not payment_method:
            payment_method_id = int(receipt_item["payment_method"])
            if payment_method_id in [e.value for e in modulkassa_api.PaymentMethod]:
                payment_method_enum = modulkassa_api.PaymentMethod(payment_method_id)
                payment_method = payment_method_enum.name.lower()
            else:
                payment_method = (
                    "advance" if receipt["billorder"] is None else "full_payment"
                )
        else:
            try:
                payment_method_value = int(payment_method)
                payment_method_enum = modulkassa_api.PaymentMethod(payment_method_value)
                payment_method = payment_method_enum.name.lower()
            except (ValueError, TypeError):
                logger.info("Unknown payment_method in config, fallback to 'full_payment'")
                payment_method = "full_payment"

        logger.info(f"Resolved payment_method: {payment_method}")
        return payment_method


    def __resolve_payment_object(self, receipt: db.Record, receipt_item: db.Record) -> str:
        """
        Determines the payment object.
        
        """

        logger.info("__RESOLVE_PAYMENT_OBJECT IS RUNNING")

        payment_object = conf.get_param("ReceiptDefaultPaymentObject")

        payment_object_id = None

        if payment_object:
            try:
                payment_object_value = int(payment_object)
                payment_object_enum = modulkassa_api.PaymentObject(payment_object_value)
                payment_object_id = payment_object_enum.value
            except (ValueError, TypeError):
                logger.info("Unknown payment_object in config")

        if payment_object_id is None:
            payment_object_candidate = int(receipt_item["payment_object"])
            if payment_object_candidate in [e.value for e in modulkassa_api.PaymentObject]:
                payment_object_id = payment_object_candidate
            elif receipt["billorder"] is None:
                payment_object_id = modulkassa_api.PaymentObject.PAYMENT.value
            else:
                payment_object_id = modulkassa_api.PaymentObject.SERVICE.value

        payment_object = modulkassa_api.PaymentObject(payment_object_id).name.lower()
        logger.info(f"Resolved payment_object: {payment_object}")
        return payment_object


    def __form_invent_positions(
        self, receipt: db.Record, receipt_items: db.Record
    ) -> modulkassa_api.InventPosition:
        """
        Constructs details from the provided receipt_items and serializes them into InventPosition.
        
        """

        logger.info("__FORM_INVENT_POSITIONS IS RUNNING")

        invent_positions = []

        for receipt_item in receipt_items:
            name = receipt_item["name"].strip()
            quantity = int(receipt_item["quantity"])
            price = float(receipt_item["price"])

            payment_method = self.__resolve_payment_method(receipt, receipt_item)
            payment_object = self.__resolve_payment_object(receipt, receipt_item)

            VAT_TAG_BILLMGR_TO_VAT_TAG_ENUM = { # pylint: disable=invalid-name
                20: modulkassa_api.VatTag.PERCENT_20.value,
                10: modulkassa_api.VatTag.PERCENT_10.value,
                0: modulkassa_api.VatTag.NO_NDS.value,
                120: modulkassa_api.VatTag.PERCENT_20_120.value,
                110: modulkassa_api.VatTag.PERCENT_10_110.value
            }
            try:
                taxrate = receipt_item["taxrate"]
                if taxrate is None:
                    logger.warning(f"receipt_{receipt['id']} has taxrate NULL")

                taxrate = int(taxrate)

                if taxrate not in VAT_TAG_BILLMGR_TO_VAT_TAG_ENUM:
                    if self._convert_invalid_rate_to_none_rate:
                        logger.info(
                            f"receipt_{receipt['id']}: Unsupported taxrate {taxrate}. "
                            "Falling back to NO_NDS due to convert_invalid_rate_to_none_rate=True"
                        )
                        vat_tag = VAT_TAG_BILLMGR_TO_VAT_TAG_ENUM[0]
                    else:
                        raise ValueError(
                            f"Invalid taxrate value: {taxrate}. "
                            f"Supported values are: {list(VAT_TAG_BILLMGR_TO_VAT_TAG_ENUM.keys())}"
                        )
                else:
                    vat_tag = VAT_TAG_BILLMGR_TO_VAT_TAG_ENUM[taxrate]

            except (ValueError, TypeError) as e:
                error_message = (
                    f"Ошибка при обработке ставки для позиции '{name}': некорректная сумма налога"
                )
                logger.error(error_message)
                misc.Mgrctl(
                    "payment_receipt.error",
                    elid=receipt["id"],
                    externalid=receipt["externalid"],
                    error_message=error_message,
                )
                raise ValueError(error_message) from e

            vat_sum = None

            if not self._convert_invalid_rate_to_none_rate or vat_tag != "none":
                vat_sum = round(float(receipt_item.get("taxamount", 0)), 2)

            invent_position = modulkassa_api.InventPosition(
                name=name,
                price=price,
                quantity=quantity,
                vatTag=vat_tag,
                vatSum=vat_sum,
                paymentMethod=payment_method,
                paymentObject=payment_object
            )

            invent_positions.append(invent_position)

        return invent_positions


    def __form_document(
        self, receipt: db.Record, invent_positions: List[modulkassa_api.InventPosition]
        ) -> modulkassa_api.Document:
        """
        Constructs details from the provided receipt and serializes them into Document.
        
        """

        logger.info("__FORM_DOCUMENT IS RUNNING")

        # Create receipt details
        external_id = receipt["external_id"]
        doc_type = modulkassa_api.DocType(receipt["receipt_type"]).name
        checkout_date_time = receipt["createdate"]
        email = receipt["email"]

        # Generate docNum
        date_str = checkout_date_time.strftime("%Y%m%d")
        time_str = checkout_date_time.strftime("%H%M%S")
        unique_id = str(uuid.uuid4())
        doc_num = f"{doc_type}-{date_str}_{time_str}_{unique_id}"

        # Get server timezone
        checkout_date_time = self.__apply_server_tz(checkout_date_time)
        checkout_datetime_iso = checkout_date_time.isoformat()

        # Form money positions
        if receipt["payment_type"] is None:
            if self.is_receipt_expense(receipt["id"]):
                payment_type = modulkassa_api.PaymentType.PREPAID.name.upper()
            else:
                payment_type = modulkassa_api.PaymentType.CARD.name.upper()
        else:
            payment_type_enum = modulkassa_api.PaymentType(receipt["payment_type"])
            payment_type = payment_type_enum.name.upper()

        money_position = modulkassa_api.MoneyPosition(
        paymentType=payment_type,
        sum=float(receipt["amount"]),
        )

        return modulkassa_api.Document(
            id=external_id,
            docNum=doc_num,
            docType=doc_type,
            checkoutDateTime=checkout_datetime_iso,
            email=email,
            inventPositions=[pos._asdict() for pos in invent_positions],
            moneyPositions=[money_position._asdict()],
        )


    def check_connection(self) -> None:
        """
        Connect cashregister to Modulkassa
        
        """

        logger.info("CHECK_CONNECTION IS RUNNING")

        try:
            xml = session.get_input_xml()

            url = xml.findtext(".//url", default="")
            username = xml.findtext(".//username", default="")
            password = xml.findtext(".//password", default="")
            retailpointid = xml.findtext(".//retailpointid", default="")

            response = self.__authorize_cashregister(
                url, username, password, retailpointid
            )

            json_response = response.json()
            status_fn = json_response["status"]

            # ! On test mode with api: https://my.modulkassa.ru/api/fn status_fn
            # is always ASSOCIATED
            if status_fn in (
                modulkassa_api.FNStatus.ASSOCIATED.name,
                modulkassa_api.FNStatus.DISABLED.name
                ):
                logger.warning(
                    f"check_connection: fiscalization_service status wrong {status_fn}"
                )

                raise modulkassa_api.ServiceUnavailable(status_fn)

            logger.info("check_connection: module connected successfuly")

        except Exception as err: # pylint: disable=broad-except
            exc.log_backtrace()
            if isinstance(err, exc.XmlException):
                xml_err = err
            else:
                xml_err = exc.XmlException(
                    err_type=Feature.CHECK_CONNECTION.value, err_value=str(err)
                )
            logger.info(f"check_connection: XML error: {xml_err}")
            logger.info(f"check_connection: XML error as xml: {xml_err.as_xml()}")
            print(xml_err.as_xml())


    def __set_status_in_billmgr_after_send(self, receipt: db.Record, document_details) -> None:
        """
        Updates the receipt status in BILLmanager according to Modulkassa's document status
        
        """

        status = document_details.status
        logger.info(f"__set_status_in_billmgr_after_send: status={status}")

        elid = receipt.as_str("id")
        externalid = receipt["external_id"]

        if status in (
            modulkassa_api.DocumentStatus.QUEUED.name,
            modulkassa_api.DocumentStatus.PENDING.name,
            modulkassa_api.DocumentStatus.WAIT_FOR_CALLBACK.name,
            modulkassa_api.DocumentStatus.REQUEUED.name,
        ):
            misc.Mgrctl("payment_receipt.wait", elid=elid, externalid=externalid)
            logger.info(
                f"send_receipt: payment_receipt get wait elid={elid}, externalid={externalid}"
            )

        elif status in (
            modulkassa_api.DocumentStatus.COMPLETED.name,
            modulkassa_api.DocumentStatus.PRINTED.name,
        ):
            misc.Mgrctl(
                "payment_receipt.success",
                elid=elid,
                externalid=externalid,
                fn_number=document_details.fiscalInfo.fnNumber,
                fiscal_document_number=document_details.fiscalInfo.fnDocNumber,
                fiscal_document_attribute=document_details.fiscalInfo.fnDocMark,
                receiptdate=document_details.fiscalInfo.receiptdate,
                receiptdate_tz=document_details.fiscalInfo.receiptdate_tz
            )
            logger.info(
                f"send_receipt: payment_receipt get success elid={elid}, externalid={externalid}"
            )

        elif status == modulkassa_api.DocumentStatus.FAILED.name:
            misc.Mgrctl(
                "payment_receipt.error",
                elid=elid,
                externalid=externalid,
                error_message=document_details.failureInfo.message,
            )
            logger.info(
                f"send_receipt: payment_receipt get error elid={elid}, externalid={externalid}"
            )

        else:
            logger.info(
                f"send_receipt: payment_receipt get unknown elid={elid}, externalid={externalid}"
            )


    def send_one_receipt(self, receipt: db.Record) -> None:
        """
        Setting receipts' status according to responses of send request from Modulkassa.
        
        """

        logger.info(f"send_receipt: receipt={receipt}")
        external_id = receipt["external_id"]
        logger.info(f"send_receipt: external_id={external_id}")


        # 1. Send document to extenal system
        receipt_items = self.__get_receipt_item_from_billmgr(payment_receipt=receipt["id"])
        invent_positions = self.__form_invent_positions(receipt, receipt_items)
        document = self.__form_document(receipt, invent_positions)
        response = modulkassa_api.send_receipt_to_external_system(
            auth=self.api_auth, document=document
        )
        if not response.ok:
            logger.warning(
                f"send_receipt: sending receipt is fail {response.status_code}"
            )
            return

        # 2. Set status and external id in BILLmanager
        document_details = modulkassa_api.parse_document_details(response)
        logger.info(f"send_receipt: receipt's data={document_details}")

        self.__set_status_in_billmgr_after_send(receipt, document_details)


    def send_receipts(self, cash_register: int) -> None:
        """
        File lock to synchronize the operation of send_receipt with other operations.
        
        """

        self.__init_cashregister(cash_register)

        with misc.FileLock(
            f"tmp/.crmodulkassa/{MODULE}"
            f"_{self.__sanitize_string(self._username)}_{self.__sanitize_string(self._url)}"
            f"_{self.__sanitize_string(self._retailpointid)}.lock",
            lock_mode=misc.FileLock.LockMode.WAIT
        ) as _:
            self.send_receipts_no_lock(cash_register)


    def send_receipts_no_lock(self, cash_register: int) -> None:
        """
        Send receipts from BILLmanager to Modulkassa.
        
        """

        logger.info(f"SEND_RECEIPTS IS RUNNING: cash_register={cash_register}")

        # 1. Check fiscalization service's status
        status_fn = self.__check_service_status()
        if status_fn is False:
            return

        # 2. Get info about new reciepts from DB
        receipts = self.__get_receipt_from_billmgr(
            cash_register, ReceiptStatus.New
        )
        if not receipts:
            return

        for receipt in receipts:
            try:
                self.send_one_receipt(receipt)
            except Exception as err: # pylint: disable=broad-except
                logger.warning(f"Smth went wrong during SEND_RECEIPT - {err}")


    def prepared_one_receipt(self, receipt: db.Record) -> None:
        """
        Setting manually sent receipts' status according to responses
        of send request from Modulkassa.
        
        """

        logger.info(f"prepared_receipt: receipt={receipt}")
        external_id = receipt["external_id"]
        logger.info(f"prepared_receipt: external_id={external_id}")

        # 1. Send document to extenal system
        receipt_items = self.__get_receipt_item_from_billmgr(payment_receipt=receipt["id"])
        invent_positions = self.__form_invent_positions(receipt, receipt_items)
        document = self.__form_document(receipt, invent_positions)
        response = modulkassa_api.send_receipt_to_external_system(
            auth=self.api_auth, document=document
        )
        if not response.ok:
            logger.warning(
                f"prepared_receipt: sending receipt is fail {response.status_code}"
            )
            return

        # 2. Set status and external id in BILLmanager
        document_details = modulkassa_api.parse_document_details(response)
        logger.info(f"prepared_receipt: receipt's data={document_details}")

        self.__set_status_in_billmgr_after_send(receipt, document_details)


    def prepared_receipts(self, cash_register: int) -> None:
        """
        File lock to synchronize the operation of prepared_receipt with other operations.
        
        """

        self.__init_cashregister(cash_register)

        with misc.FileLock(
            f"tmp/.crmodulkassa/{MODULE}"
            f"_{self.__sanitize_string(self._username)}_{self.__sanitize_string(self._url)}"
            f"_{self.__sanitize_string(self._retailpointid)}.lock",
            lock_mode=misc.FileLock.LockMode.WAIT
        ) as _:
            self.prepared_receipts_no_lock(cash_register)


    def prepared_receipts_no_lock(self, cash_register: int) -> None:
        """
        Send prepared receipts from BILLmanager to Modulkassa.
        """

        logger.info(f"PREPARED_RECEIPTS IS RUNNING: cash_register={cash_register}")

        # 1. Check fiscalization service's status
        status_fn = self.__check_service_status()
        if status_fn is False:
            return

        # 2. Get info about new reciepts from DB
        receipts = self.__get_receipt_from_billmgr(
            cash_register, ReceiptStatus.Prepare
        )
        if not receipts:
            return

        for receipt in receipts:
            try:
                self.prepared_one_receipt(receipt)
            except Exception as err: # pylint: disable=broad-except
                logger.warning(f"Smth went wrong during PREPARED_RECEIPT - {err}")


    def check_one_receipt(self, receipt: db.Record) -> None:
        """
        Setting receipts' status according to responses of check request from Modulkassa.
        
        """

        logger.info(f"check_receipt: receipt={receipt}")
        external_id = receipt["external_id"]
        logger.info(f"check_receipt: external_id={external_id}")

        # 1. Get receipt from extenal system
        response = modulkassa_api.get_receipt_from_external_system(
            auth=self.api_auth, external_id=receipt.as_str("external_id")
        )
        if not response.ok:
            logger.warning(
                f"check_receipt: getting receipt is fail {response.status_code}"
            )
            return

        # 2. Set status and external id in BILLmanager
        document_details = modulkassa_api.parse_document_details(response)
        logger.info(f"check_receipt: receipt's data={document_details}")

        status = document_details.status
        logger.info(f"check_receipt: receipt's status={status}")

        # ! on test mode with api: https://my.modulkassa.ru/api/fn receipt is always QUEUED
        if status in (
            modulkassa_api.DocumentStatus.QUEUED.name,
            modulkassa_api.DocumentStatus.PENDING.name,
            modulkassa_api.DocumentStatus.WAIT_FOR_CALLBACK.name,
            modulkassa_api.DocumentStatus.REQUEUED.name,
        ):
            logger.info(
                f"check_receipt: payment_receipt get wait elid={receipt.as_str('id')}, "
                f"externalid={external_id}"
            )

        elif status in (
            modulkassa_api.DocumentStatus.COMPLETED.name,
            modulkassa_api.DocumentStatus.PRINTED.name,
        ):
            misc.Mgrctl(
                "payment_receipt.success",
                elid=receipt.as_str("id"),
                externalid=external_id,
                fn_number=document_details.fiscalInfo.fnNumber,
                fiscal_document_number=document_details.fiscalInfo.fnDocNumber,
                fiscal_document_attribute=document_details.fiscalInfo.fnDocMark,
                receiptdate=document_details.fiscalInfo.receiptdate,
                receiptdate_tz=document_details.fiscalInfo.receiptdate_tz
            )
            logger.info(
                f"check_receipt: payment_receipt get success elid={receipt.as_str('id')}, "
                f"externalid={external_id}"
            )

        elif status in (modulkassa_api.DocumentStatus.FAILED.name):
            misc.Mgrctl(
                "payment_receipt.error",
                elid=receipt.as_str("id"),
                externalid=external_id,
                error_message=document_details.failureInfo.message,
            )
            logger.info(
                f"check_receipt: payment_receipt get error elid={receipt.as_str('id')}, "
                f"externalid={external_id}"
            )

        else:
            logger.info(
                f"check_receipt: payment_receipt got unknown status "
                f"elid={receipt.as_str('id')}, "
                f"externalid={external_id}"
            )


    def check_receipts(self, cash_register: int) -> None:
        """
        File lock to synchronize the operation of check_receipt with other operations.
        
        """

        self.__init_cashregister(cash_register)

        with misc.FileLock(
            f"tmp/.crmodulkassa/{MODULE}"
            f"_{self.__sanitize_string(self._username)}_{self.__sanitize_string(self._url)}"
            f"_{self.__sanitize_string(self._retailpointid)}.lock",
            lock_mode=misc.FileLock.LockMode.WAIT
        ) as _:
            self.check_receipts_no_lock(cash_register)


    def check_receipts_no_lock(self, cash_register: int) -> None:
        """
        Request receipts' statuses from BILLmanager to Modulkassa.
        
        """

        logger.info(f"CHECK_RECEIPTS IS RUNNING: cash_register={cash_register}")

        # 1. Check fiscalization service's status
        status_fn = self.__check_service_status()
        if status_fn is False:
            return

        # 2. Get info about new reciepts from DB
        receipts = self.__get_receipt_from_billmgr(
            cash_register, ReceiptStatus.Wait
        )
        if not receipts:
            return

        for receipt in receipts:
            try:
                self.check_one_receipt(receipt)
            except Exception as err: # pylint: disable=broad-except
                logger.warning(f"Smth went wrong during CHECK_RECEIPT - {err}")


if __name__ == "__main__":
    ModulkassaRegister().run()
