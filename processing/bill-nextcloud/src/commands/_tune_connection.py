import billmgr.session as session
import xml.etree.ElementTree as ET
from utils.api import (
    NextCloudAPIClient,
    NextCloudUserService,
)
from pmnextcloud import LOGGER
from billmgr.exception import XmlException


def tune_connection():
    xml = session.get_input_xml()
    base_url_node = xml.find("./base_url")
    username_node = xml.find("./nc_username")
    password_node = xml.find("./nc_password")
    func_node = xml.find("./func")
    if func_node is not None and func_node.text == "processing.add.user":
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
    ET.dump(xml)
