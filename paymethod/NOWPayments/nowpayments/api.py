import json
import traceback
from typing import Optional, List, Dict

import requests

from billmgr.logger import get_logger

from nowpayments.enums import SortBy, OrderBy
from nowpayments.exceptions import NotOkException, InvalidResponseException


MODULE = "nowpayments_api"


class NOWPaymentsAPI:
    def __init__(self,
                 api_key: str = "",
                 is_test: bool = True,
                 ):
        """Keyword arguments:
        api_key -- api key specified in the paymethod's xml_params
        is_test -- indicator that the API URL is sandbox or not
        """
        self.__api_key = api_key
        self.__is_test = is_test
        self.__url = self.__get_api_url()
        get_logger(MODULE).info(
            f"Making a request for paymethod which has api_key = {self.mask_key()} and is_test = {is_test}")

    def is_api_ok(self) -> bool:
        response = requests.request(
            "GET", f"{self.__url}/status", timeout=10)
        return response.ok

    def get_payment_url(self) -> str:
        """Return the API URL depending on whether this paymethod is sandbox or not

        Keyword arguments:
        is_test -- indicator that the API URL is sandbox or not
        """
        if self.__is_test is False:
            return "https://nowpayments.io/payment"
        return "https://sandbox.nowpayments.io/payment"

    def __get_api_url(self) -> str:
        """Return the API URL depending on whether this paymethod is sandbox or not

        Keyword arguments:
        is_test -- indicator that the API URL is sandbox or not
        """
        if self.__is_test is False:
            return "https://api.nowpayments.io/v1"
        return "https://api-sandbox.nowpayments.io/v1"

    def get_payments_by_invoice(self,
                                jwt_token: str = "",
                                invoice_id: int = 0,
                                limit: int = 500,
                                ) -> List:
        """Get list of payments from NOWPayments by invoice id

        Keyword arguments:
        jwt_token -- token generated using the get_jwt_token() function
        invoice_id -- this payment's invoice id
        limit -- number of records in one page. (possible values: from 1 to 500)
        """
        get_logger(MODULE).info(f"get payments by invoice {invoice_id}")
        page = 0
        payments: List = []

        # loop until error 400 (wrong page)
        while True:
            try:
                pays = self.__get_payments_on_page(
                    jwt_token=jwt_token,
                    limit=limit,
                    page=page,
                    invoice_id=invoice_id,
                )
                get_logger(MODULE).info(pays)
            except NotOkException:
                break

            page += 1
            payments.extend(pays)

        if isinstance(payments, List) and len(payments) == 0:
            get_logger(MODULE).info(
                f"No payments have been found for invoice id {invoice_id}")
            payments = []

        elif not isinstance(payments, List) or payments is None:
            raise InvalidResponseException(
                f"Encountered invalid response while getting payments by invoice id {invoice_id}")

        return payments

    def __get_payments_on_page(self,
                               jwt_token: str = "",
                               limit: int = 500,
                               page: int = 0,
                               sort_by: str = SortBy.CREATED_AT,
                               order_by: str = OrderBy.DESC,
                               date_from: Optional[str] = None,
                               date_to: Optional[str] = None,
                               invoice_id: Optional[int] = None,
                               ) -> List:
        """Get list of payments (dicts) on the specified page in accordance to the specified limit

        Keyword arguments:
        jwt_token -- token generated using the get_jwt_token() function
        limit -- number of records in one page. (possible values: from 1 to 500)
        page -- number of page
        sort_by -- sort the received list by a paramenter chosen from the NOWPaymentsSortBy class
        order_by -- display the list in ascending or descending order (possible values: asc, desc)
        date_from -- start date (date format: YYYY-MM-DD or yy-MM-ddTHH:mm:ss.SSSZ)
        date_to -- end date (date format: YYYY-MM-DD or yy-MM-ddTHH:mm:ss.SSSZ)
        invoice_id -- this payment's invoice id
        """
        url = f"{self.__url}/payment/?limit={limit}&page={page}&sortBy={sort_by}&orderBy={order_by}"
        if date_from is not None:
            url += f"&dateFrom={date_from}"
        if date_to is not None:
            url += f"&dateTo={date_to}"
        if invoice_id is not None:
            url += f"&invoiceId={invoice_id}"
        get_logger(MODULE).info(url)

        headers = {
            "x-api-key": self.__api_key,
            "Authorization": f"Bearer {jwt_token}"
        }
        response = requests.request(
            "GET", url, headers=headers, data={}, timeout=30)

        if not response.ok:
            raise NotOkException(f"Failed to get payments on page with {url}")

        data: List = response.json().get("data")

        if isinstance(data, List) and len(data) == 0:
            get_logger(MODULE).info(
                f"No data has been found while getting payments on page with {url}")
            data = []

        elif data is None or not isinstance(data, List):
            raise InvalidResponseException(
                f"Encountered invalid \"data\" object while getting payments on page with {url}\n"
                f"The object is {type(data)} of value {data}")

        return data

    def get_first_payment(self,
                          jwt_token: str = "",
                          invoice_id: str = "",
                          ) -> Dict:
        """Get list of payments (dicts) on the specified page in accordance to the specified limit

        Keyword arguments:
        jwt_token -- token generated using the get_jwt_token() function
        invoice_id -- this payment's invoice id
        """
        url = f"{self.__url}/payment/?limit=1&page=0&invoiceId={invoice_id}"
        get_logger(MODULE).info(url)

        headers = {
            "x-api-key": self.__api_key,
            "Authorization": f"Bearer {jwt_token}"
        }
        response = requests.request(
            "GET", url, headers=headers, data={}, timeout=10)

        if not response.ok:
            raise NotOkException(f"Failed to get first payment with {url}")

        data: List = response.json().get("data")

        if isinstance(data, List) and len(data) == 0:
            get_logger(MODULE).info(
                f"No data has been found while getting first payment with {url}")
            data = []

        elif data is None or not isinstance(data, List):
            raise InvalidResponseException(
                f"Encountered invalid \"data\" object while getting first payment with {url}\n"
                f"The object is {type(data)} of value {data}")

        return data[0]

    def get_jwt_token(self,
                      email: str = "",
                      password: str = "",
                      ) -> str:
        """
        Generate token for the given email and password pair 
        to gain access to methods such as getting payments, etc.
        The generated token remains valid for five minutes.

        Keyword arguments:
        email -- NOWPayments email specified in the paymethod's xml_params
        password -- NOWPayments password specified in the paymethod's xml_params
        """
        url_auth = f"{self.__url}/auth"
        payload = {
            "email": email,
            "password": password
        }

        response = requests.request(
            "POST", url_auth, headers={}, data=payload, timeout=10)
        if not response.ok:
            raise NotOkException(
                f"Failed to generate token for user {email} using {url_auth} and {payload}."
                f"In response got {response.text}")

        token: Dict = response.json()

        if not isinstance(token, Dict) or len(token) == 0 or token.get("token") is None:
            raise InvalidResponseException(
                f"Encountered invalid response while getting token "
                f"using {url_auth} and {payload}. In response got {response.text}.\n"
                f"The object is {type(token)} of value {token}")

        return token.get("token")

    def get_currencies(self) -> List[str]:
        """
        Get list of available currencies
        """
        url = f"{self.__url}/currencies"
        headers = {
            "x-api-key": self.__api_key,
        }

        response = requests.request("GET", url, headers=headers, timeout=10)
        if not response.ok:
            raise NotOkException("Failed to retrieve currencies")

        currencies: List = response.json().get("currencies")

        if currencies is None or not isinstance(currencies, List) or len(currencies) == 0:
            raise InvalidResponseException(
                f"Encountered invalid response while getting currencies.\n"
                f"The object is {type(currencies)} of value {currencies}")

        return currencies

    def is_valid_api_key(self) -> bool:
        """
        Check if given api_key is valid (exists)
        """
        currencies = self.get_currencies()
        return bool(currencies)

    def is_valid_api_auth(self,
                          jwt_token: str = ""
                          ) -> bool:
        """Check if given api_key and token are related to the same account

        Keyword arguments:
        jwt_token -- token generated using the get_jwt_token() function
        """
        payments = self.__get_payments_on_page(jwt_token, limit=1)
        return "status" not in payments

    def get_invoice(self,
                    price_amount: float,
                    price_currency: str,
                    order_id: str,
                    description: str,
                    success_url: str,
                    cancel_url: str
                    ) -> Dict:
        """Create a payment link and return response in the json format

        Keyword arguments:
        price_amount -- this payment"s money amount in price_currency
        price_currency -- this paymethod"s fiat currency, e.g. usd, euro, etc.
        order_id -- this payment's BILLmanager number
        description -- this payment's description
        success_url -- url to which the client will be redirected to after
            successful payment
        cancel_url -- url to which the client will be redirected to after
            failed payment
        """
        headers = {
            "x-api-key": self.__api_key,
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "price_amount": price_amount,
            "price_currency": price_currency,
            "order_id": order_id,
            "order_description": description,
            "is_fixed_rate": True,
            "success_url": success_url,
            "cancel_url": cancel_url,
        })
        url = f"{self.__url}/invoice"
        try:
            response = requests.request(
                "POST", url, headers=headers, data=data, timeout=10)
            if not response.ok:
                raise NotOkException(
                    f"Failed to create invoice for {order_id}")

            invoice: Dict = response.json()

            if not isinstance(invoice, Dict) or \
               len(invoice) == 0 or  \
               invoice.get("invoice_url") is None:
                raise InvalidResponseException(
                    f"Encountered invalid response while getting invoice "
                    f"using {headers} and {data}.\n"
                    f"The object is {type(invoice)} of value {invoice}")

            return invoice
        except Exception as e:
            if isinstance(e, ValueError):
                get_logger(MODULE).error(e)
            else:
                get_logger(MODULE).error(traceback.format_exc())

            raise Exception from e

    def mask_key(self):
        '''Creates a mask for the key
        '''
        parts = self.__api_key.split('-')
        parts[1] = '*' * len(parts[1])
        parts[2] = '*' * len(parts[2])
        masked_key = '-'.join(parts)
        return masked_key
