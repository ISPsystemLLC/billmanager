from utils.api import CloudClientFactory
import billmgr.misc as misc
from utils.misc import User
from billmgr.exception import XmlException
from pmnextcloud import LOGGER


def close(item: int) -> None:
    api_client, user_service, group_service = (
        CloudClientFactory.create_client_from_item(item)
    )
    try:
        user = User(item, user_service)
        user_service.delete_user(user.username)
    except Exception as e:
        LOGGER.error("Can't delete user account")
        if "404" in str(e):
            LOGGER.error(
                "The account doesn't exist, or it may have been manually deleted from the Nextcloud panel. In this case, you need to resolve the issue manually."
            )
        raise XmlException(f"close_error: {e}") from e
    else:
        misc.postclose(item)
