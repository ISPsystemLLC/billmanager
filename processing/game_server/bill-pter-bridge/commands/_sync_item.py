'''
    Модуль реализует функцию sync_item .
'''
import billmgr.misc as misc
import utils.misc as utils


def sync_item(item):
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    pterapi = utils.pter_api_key(item)
    status = misc.iteminfo(item)['status']
    exist_in_pter = utils.is_server_exist(item)
    if exist_in_pter:
        if status == 3 and pterapi.servers.get_server_info(external_id=str(item))['status'] != 'suspended':
            pterapi.servers.suspend_server(pterapi.servers.get_server_info(external_id=str(item))['id'])
        #utils.sync_params(item)
    elif status not in {1, 4, 5}:
        pass
