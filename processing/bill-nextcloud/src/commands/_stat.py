from utils.api import CloudClientFactory
import billmgr.misc as misc
from utils.misc import User, from_multiple_get_key, get_stat_measure
from datetime import datetime, date
from pmnextcloud import LOGGER
from utils.consts import DISK_SPACE, DISK_SPACE_DEFAULT, MEASURE_DEFAULT


def stat(module: int) -> None:
    items = misc.get_items_for_sync(module)
    LOGGER.info(f"Items to get stat {items}")
    if items:
        api_client, user_service, group_service = (
            CloudClientFactory.create_client_from_item(next(iter(items)))
        )
    for item in items:
        try:
            user = User(item, user_service)
            user_data = user_service.get_user_data(user.username)

            quota_data = user_data["ocs"]["data"]["quota"]
            param = from_multiple_get_key(
                misc.itemaddons(item), DISK_SPACE, DISK_SPACE_DEFAULT[1]
            )
            stat_measure = get_stat_measure(item)
            quota_to_stat = 0

            try:
                quota_to_stat = int(quota_data["used"]) * misc.get_relation(
                    MEASURE_DEFAULT, stat_measure
                )
            except Exception as e:
                LOGGER.error(f"Can't calculate quota for item {item}: {e}")

            misc.insert_stat(item, datetime.now(), param, quota_to_stat, stat_measure)

        except KeyError as e:
            if "ocs" in str(e) or "data" in str(e) or "quota" in str(e):
                LOGGER.warning(f"Quota data missing for item {item}: {e}")
            else:
                LOGGER.error(f"Unexpected KeyError for item {item}: {e}")

        except Exception as e:
            if "User does not exist" in str(e):
                LOGGER.warning(f"Skipping item {item} — user does not exist: {e}")
            else:
                LOGGER.error(f"Can't get quota for item {item} with error: {e}")

    misc.poststat(module, date.today())
