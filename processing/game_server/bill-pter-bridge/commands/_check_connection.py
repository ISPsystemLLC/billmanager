'''
    Модуль реализует функцию check_connection .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-check_connection
'''
import xml.etree.ElementTree as ET
from pydactyl import PterodactylClient
import billmgr.exception
import billmgr.session as session


from utils.logger import logger

def check_connection() -> None:
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    xml = session.get_input_xml()
    session.debug_session(xml)
    logger.debug(f'xml params:{ET.tostring(xml)}')
    logger.info("get xml parameters")
    panelurl_node = xml.find('./processingmodule/base_url')
    logger.info("parse panel_url xml node")
    api_key_node = xml.find('./processingmodule/api_key')
    logger.info("parse api_key xml node")
    admin_api_key_node = xml.find('./processingmodule/admin_api_key')
    logger.info("parse admin_api_key xml node")
    api_key = api_key_node.text if api_key_node is not None else ''
    base_url = panelurl_node.text if panelurl_node is not None else ''
    logger.info("pre-panel inited")
    admin_api_key = admin_api_key_node.text if admin_api_key_node is not None else ''
    panel_api = PterodactylClient(base_url, api_key)
    admin_api = PterodactylClient(base_url, admin_api_key)
    logger.info("panel inited")
    try:
        logger.info("checking")
        panel_api.servers.list_servers()
        admin_api.client.account.api_key_list()
    except Exception as ex:
        logger.info("catch exception")
        #В billmgr_mod_pmpter.xml прописываются сообщения в формате msg_error_тип,
        # напримере нижнего выражения msg_error_wrong_panel_info,
        # доки:  https://www.ispsystem.ru/docs/coremanager/razrabotchiku/obshchie-spetsifikatsii/oshibki
        raise billmgr.exception.XmlException('wrong_panel_info')
    xml_out = session.new_node("doc", '')
    xml_out.append(session.new_node('ok', ''))
    ET.dump(xml_out)
