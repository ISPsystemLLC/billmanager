'''
    Модуль реализует функцию delip .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-delip
'''
from pydactyl.exceptions import PterodactylApiError

import billmgr.db as db
import billmgr.misc as misc

from utils.misc import order_params
from utils.misc import pter_api_key
from utils.misc import get_allocation_id
from utils.logger import logger


def del_ip(item, ip_id):
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    logger.info("delip command started")
    old_address = db.db_query(f'''SELECT name FROM ip WHERE  id = %s''', ip_id)[0]['name']
    old_ip, old_port = old_address.split(':')
    logger.extinfo(f'old_ip: {old_address}')
    pterapi = pter_api_key(item)
    server = pterapi.servers.get_server_info(external_id=item, includes={'allocations'})
    server_id = server['id']
    logger.debug(f'server_id: {server_id}')
    limits = server['limits']
    limits2 = server['feature_limits']
    alloc_id = get_allocation_id(item, old_ip, old_port)
    allocations_limit = order_params(item)['ip']
    try:
        pterapi.servers.update_server_build(server_id=server['id'],
                                            allocation_id=server['allocation'],
                                            memory_limit=limits['memory'],
                                            swap_limit=limits['swap'],
                                            disk_limit=limits['disk'],
                                            cpu_limit=limits['cpu'],
                                            io_limit=limits['io'],
                                            database_limit=limits2['databases'],
                                            allocation_limit=allocations_limit,
                                            backup_limit=limits2['backups'],
                                            remove_allocations=[int(alloc_id)])
        misc.del_ip(ip_id=ip_id)
    except PterodactylApiError as err:
        if "You are attempting to delete the default allocation" in str(err.args):
            for i in server['relationships']['allocations']['data']:
                if str(i['attributes']['id']) != str(server['allocation']):
                    pterapi.servers.update_server_build(server_id=server['id'],
                                                        allocation_id=int(i['attributes']['id']),
                                                        memory_limit=limits['memory'],
                                                        swap_limit=limits['swap'],
                                                        disk_limit=limits['disk'],
                                                        cpu_limit=limits['cpu'],
                                                        io_limit=limits['io'],
                                                        database_limit=limits2['databases'],
                                                        allocation_limit=allocations_limit,
                                                        backup_limit=limits2['backups'],
                                                        remove_allocations=[int(server['allocation'])])
                    misc.del_ip(ip_id=ip_id)
                    break
            else:
                logger.error('''You are attempting to delete
                 the default allocation while there is only one allocation''')
    
