'''
    Модуль реализует функцию resume .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-resume
'''
import billmgr.misc as misc
from utils.misc import pter_api_key
from utils.misc import control_server_state


def resume(item: int) -> None:
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    pterapi = pter_api_key(item)
    pterapi.servers.unsuspend_server(pterapi.servers.get_server_info(external_id=str(item))['id'])
    misc.postresume(item)
    control_server_state(item, 'start')
