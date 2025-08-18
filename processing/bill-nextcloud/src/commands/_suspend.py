from utils.api import CloudClientFactory
import billmgr.misc as misc
from utils.misc import User
from billmgr.exception import XmlException
from pmnextcloud import LOGGER


def suspend(item: int) -> None:
    api_client, user_service, group_service = (
        CloudClientFactory.create_client_from_item(item)
    )
    try:
        user = User(item, user_service)
        user_service.suspend_user(user.username)
    except Exception as e:
        LOGGER.error("Can't suspend user account")
        raise XmlException(f"suspend_error: {e}") from e
    else:
        misc.postsuspend(item)
