from enum import Enum


class OrderBy(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortBy(str, Enum):
    CREATED_AT = "created_at"
    PAYMENT_ID = "payment_id"
    PAYMENTS_STATUS = "payment_status"
    PAY_ADDRESS = "pay_address"
    PRICE_AMOUNT = "price_amount"
    PRICE_CURRENCY = "price_currency"
    PAY_AMOUNT = "pay_amount"
    ACTUALLY_PAID = "actually_paid"
    PAY_CURRENCY = "pay_currency"
    ORDER_ID = "order_id"
    ORDER_DESCRIPTION = "order_description"
    PURCHASE_ID = "purchase_id"
    OUTCOME_AMOUNT = "outcome_amount"
    OUTCOME_CURRENCY = "outcome_currency"


class PaymentStatus(str, Enum):
    # Waiting the client to send the payment. The initial status of each payment.
    WAITING = "waiting"
    # Appears when NOWPayments detect the funds from the client on the blockchain.
    CONFIRMING = "confirming"
    # Client’s funds have accumulated enough confirmations.
    CONFIRMED = "confirmed"
    # The funds are being sent to the provider's personal wallet.
    SENDING = "sending"
    # Shows that the client sent the less than the actual price.
    PARTIALLY_PAID = "partially_paid"
    # The funds have reached the provider's personal address and the payment is finished.
    FINISHED = "finished"
    # The payment wasn't completed due to the error of some kind.
    FAILED = "failed"
    # The funds were refunded back to the client.
    REFUNDED = "refunded"
    # The client didn't send the funds to the specified address in the 7 days time window
    EXPIRED = "expired"
