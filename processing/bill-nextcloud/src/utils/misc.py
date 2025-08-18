import billmgr.db as db
import billmgr.misc as misc
import secrets
import string
from utils.consts import DISK_SPACE, DISK_SPACE_DEFAULT, MEASURE_DEFAULT  # MEASURE_DICT
from pmnextcloud import LOGGER


def get_stat_measure(item: int):
    quota = from_multiple_keys(misc.itemaddons(item), DISK_SPACE, DISK_SPACE_DEFAULT)
    return quota[1]


def from_multiple_get_key(params, keys, default):
    for key in keys:
        if key in params:
            return key
    return default


def from_multiple_keys(params, keys, default):
    for key in keys:
        if key in params:
            return params[key]
    return default


def get_account_id(item):
    item_info = misc.iteminfo(item)
    return item_info["account_id"]


def get_billaccount_email(item):
    acc_id = get_account_id(item)
    return db.db_query(
        "SELECT email FROM user WHERE account=%s ORDER BY id ASC", acc_id
    )[0]["email"]


class User:
    def __init__(self, item, service):
        self.item = item
        self.service = service
        self.username = self.generate_username()
        self.email = self.get_email()
        self.exists = self.check_if_exists()
        if not self.exists:
            self.password = self.generate_password()
        self.quota = self.get_quota()
        self.usergroup = self.get_usergroup()

    def generate_username(self):
        return f"user_{self.item}"

    def get_email(self):
        return get_billaccount_email(self.item)

    def generate_password(self, length=20):
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def get_quota(self):
        quota = from_multiple_keys(
            misc.itemaddons(self.item), DISK_SPACE, DISK_SPACE_DEFAULT
        )
        return int(quota[0]) * misc.get_relation(quota[1], MEASURE_DEFAULT)

    def get_usergroup(self):
        pricelist_params = misc.get_pricelist_params(
            misc.iteminfo(self.item)["pricelist"]
        )
        return pricelist_params.get("usergroup", "")

    def get_last_usergroup(self):
        pricelist_params = misc.get_pricelist_params(
            misc.iteminfo(self.item)["lastpricelist"]
        )
        return pricelist_params.get("usergroup", "")

    def check_if_exists(self):
        return self.username in self.service.get_users(search=self.username)
