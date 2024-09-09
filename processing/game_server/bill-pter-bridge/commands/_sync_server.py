'''
    Модуль реализует функцию sync_server .
'''
import billmgr.misc as misc

from utils.logger import logger
import utils.consts as Params
from pydactyl import PterodactylClient

def sync_server(module):
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    proccesingparam = misc.get_module_params(module)
    api_key = proccesingparam['api_key']
    base_url = proccesingparam['base_url']
    pterapi = PterodactylClient(base_url, api_key)
    pages = pterapi.nests.list_nests(includes={'eggs'})
    param_values = {}
    for page in pages:
        for nest in page:
            eggs = nest['attributes']['relationships']['eggs']['data']
            for egg in eggs:
                param_values[f"{egg['attributes']['id']}_{egg['attributes']['nest']}"] = {'name' :  f"{pterapi.nests.get_nest_info(egg['attributes']['nest'])['attributes']['name']}/{egg['attributes']['name']}"}
    for itemtype in Params.ITEMTYPE:
        try:
            misc.sync_itemtype_param(module,
                                     itemtype,
                                     Params.SERVER_TYPE,
                                     param_values)
        except Exception:
            logger.extinfo(f'server_type in itemtype=\'{itemtype}\' not found')
    # pages = pterapi.locations.list_locations()
    # param_values = {}
    # for page in pages:
    #     for location in page:
    #         param_values[f"{location['attributes']['id']}"] = {'name' :  location['attributes']['short']}
    # misc.sync_itemtype_param(module, Params.ITEMTYPE, Params.LOCATION_ID, param_values)
