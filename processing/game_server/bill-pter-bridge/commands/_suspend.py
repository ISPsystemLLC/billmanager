'''
    Модуль реализует функцию suspend .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-suspend
'''

import billmgr.misc as misc
from utils.misc import pter_api_key



def suspend(item: int) -> None:
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    pterapi = pter_api_key(item)
    pterapi.servers.suspend_server(pterapi.servers.get_server_info(external_id=str(item))['id'])
    misc.postsuspend(item)
