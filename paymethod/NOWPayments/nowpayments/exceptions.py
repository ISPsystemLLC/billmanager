from billmgr.logger import get_logger


MODULE = "nowpayments_api"


class NotOkException(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        get_logger(MODULE).error(msg)


class InvalidResponseException(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        get_logger(MODULE).error(msg)
