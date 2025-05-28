'''
    Модуль реализует функцию close .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-close
'''
import billmgr.exception
import billmgr.misc as misc

from utils.misc import pter_api_key
from utils.misc import delete_server_ips
from utils.logger import logger
from utils.misc import get_account_id

def close(item, runningoperation):
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    logger.info("close called")
    api = pter_api_key(item)
    account_id = get_account_id(item)
    server = api.servers.get_server_info(external_id=str(item))
    
    logger.info(f"deleting server {server['id']}")
    try:
        api.servers.delete_server(server['id'], force=True)
        delete_server_ips(item)
    except Exception as ex:
        logger.error(f"catch exception {ex}")
        raise billmgr.exception.XmlException('server_del')
    misc.postclose(item)
