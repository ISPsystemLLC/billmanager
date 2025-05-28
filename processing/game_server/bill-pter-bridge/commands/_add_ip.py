'''
    Модуль реализует функцию add_ip .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-addip
'''
import billmgr.db as db
import billmgr.misc as misc

from utils.misc import order_params
from utils.misc import pter_api_key
from utils.logger import logger
import utils.consts as Params


def add_ip(item, ip_id):
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    with misc.FileLock(f'tmp/.tmp/{"pter_add_ip_".join(str(item))}'):
        syncronous_add_ip(item, ip_id)


def syncronous_add_ip(item, ip_id):
    logger.info("addip command started")
    elid = ip_id
    pterapi = pter_api_key(item)
    server = pterapi.servers.get_server_info(external_id=item, includes={'allocations'})
    logger.debug(f"server: {server}")
    limits = server['limits']
    limits2 = server['feature_limits']
    allocs = server['relationships']['allocations']['data']
    ip = allocs[-1]['attributes']['ip']
    port = allocs[-1]['attributes']['port']
    address = f'{ip}:{port}' 
    if db.db_query(f'SELECT * FROM ip WHERE name = %s', address):
        allocations = pterapi.nodes.list_node_allocations(node_id=server['node'])
        new_address = None
        alloc_id = None
        
        for page in allocations:
            for alloc in page:
                if not alloc['attributes']['assigned']:
                    new_address = f"{alloc['attributes']['ip']}:{alloc['attributes']['port']}"
                    logger.extinfo(f"new_address: {new_address}")
                    alloc_id = alloc['attributes']['id']
                    break
            if new_address:
                if not db.db_query(f'SELECT * FROM ip WHERE name = %s', new_address):
                    break
        if not new_address:
            raise Exception('Not enough allocations')
        logger.debug(f"order params: {order_params(item)}")
        allocations_limit = int(order_params(item)['ip'])
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
                                            add_allocations=[alloc_id])
        logger.info("server updated")
        address = new_address
    logger.info(ip)    
    
    try:
        misc.commit_ip(ip_id=misc.save_ip(ip_id=elid, ip=address, domain=''))
    except Exception as ex:
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
                                    remove_allocations=[alloc_id])
        logger.info(f"ip: {address}")
        raise ex
