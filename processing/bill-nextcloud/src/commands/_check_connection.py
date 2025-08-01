import xml.etree.ElementTree as ET
import billmgr.exception
import billmgr.session as session
from utils.api import (
    NextCloudAPIClient,
    NextCloudUserService,
)
from pmnextcloud import LOGGER
from billmgr.exception import XmlException


def check_connection() -> None:
    """Реализация комманды для проверки подключения"""
    xml = session.get_input_xml()
    session.debug_session(xml)
    LOGGER.debug(f"xml params:{ET.tostring(xml)}")
    base_url_node = xml.find("./processingmodule/base_url")
    username_node = xml.find("./processingmodule/nc_username")
    password_node = xml.find("./processingmodule/nc_password")
    base_url = base_url_node.text if base_url_node is not None else ""
    username = username_node.text if username_node is not None else ""
    password = password_node.text if password_node is not None else ""
    api = NextCloudAPIClient(base_url, username, password)
    user_service = NextCloudUserService(api)
    try:
        user_service.get_users()
    except Exception as e:
        LOGGER.error(f"Can't connect to NextCloud: {e}")
        raise XmlException("wrong_panel_info")
