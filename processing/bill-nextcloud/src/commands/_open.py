from utils.api import CloudClientFactory
import billmgr.misc as misc
from utils.misc import (
    User,
)
from pmnextcloud import LOGGER
from billmgr.exception import XmlException


def open(item: int) -> None:
    api_client, user_service, group_service = (
        CloudClientFactory.create_client_from_item(item)
    )
    user = User(item, user_service)

    if user.exists:
        raise XmlException("open_colission_error")

    try:
        user_service.create_user(user.username, user.password, user.email, user.quota)
        if user.usergroup != "":
            try:
                group_service.add_user_to_group(user.username, user.usergroup)
            except:
                LOGGER.error(f"Error during user group setup: {e}")
        misc.save_param(user.item, param="username", value=user.username)
        misc.save_param(
            user.item,
            param="userpassword",
            value=user.password,
            crypted=True,
        )
        misc.save_param(item, param="url", value=api_client.base_url)

    except Exception as e:
        LOGGER.error(f"Error during user setup: {e}")
        try:
            user_service.delete_user(user.username)
        except Exception as cleanup_error:
            LOGGER.error(f"Failed to cleanup user after error: {cleanup_error}")
        raise XmlException(f"open_error: {e}") from e

    misc.postopen(item)
