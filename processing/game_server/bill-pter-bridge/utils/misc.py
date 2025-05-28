import billmgr.db as db
import billmgr.exception
import billmgr.misc as misc
import billmgr.crypto as crypto

from pydactyl import PterodactylClient
from pydactyl.exceptions import PterodactylApiError
from requests.exceptions import HTTPError
from urllib.parse import urlparse

from utils.logger import logger
import utils.consts as Params
import secrets
import string
import random

def is_server_exist(item):
    '''
        Функция проверяет существование сервера по заданной услуге на стороне Pterodactyl
    '''
    pterapi = pter_api_key(item)
    try:
        server_info = pterapi.servers.get_server_info(external_id=str(item))
        return True
    except HTTPError:
        return False


def sync_params(item):
    '''
        Функция синхронизирует параметры услуги из billmgr в pterodactyl
    '''
    pterapi = pter_api_key(item)
    server_info = pterapi.servers.get_server_info(external_id=str(item))
    allocation_id = server_info['allocation']
    order_param = order_params(item)
    logger.info(order_param)
    pterapi.servers.update_server_build(server_id=server_info['id'],
    allocation_id=server_info['allocation'],
    memory_limit=str(order_param.get(Params.RAM_LIMIT, Params.RAM_LIMIT_DEFAULT)),
    swap_limit=str(order_param.get(Params.SWAP_LIMIT, Params.SWAP_LIMIT_DEFAULT)),
    cpu_limit=str(int(order_param.get(Params.CPU_LIMIT, Params.CPU_LIMIT_DEFAULT))*100),
    disk_limit=str(get_param_from_muliple_keys(order_param,Params.DISK_MEMORY_LIMIT,Params.DISK_MEMORY_LIMIT_DEFAULT)),
    io_limit=str(order_param.get(Params.IO_LIMIT, Params.IO_LIMIT_DEFAULT)),
    backup_limit=str(order_param.get(Params.BACKUP_LIMIT, Params.BACKUP_LIMIT_DEFAULT)),
    allocation_limit=str(order_param.get(Params.ALLOCATION_LIMIT, Params.ALLOCATION_LIMIT_DEFAULT)),
    database_limit=str(order_param.get(Params.DB_LIMIT, Params.DB_LIMIT_DEFAULT)))
    #pterapi.servers.update_server_details(server_id=server_info['id'],name=order_param[Params.SERVER_NAME],user_id=pterapi.servers.get_server_info(external_id=str(item),includes={'user'})['relationships']['user']['attributes']['id'],external_id=str(item))
    #pterapi.servers.update_server_startup(server_id=server_info['id'],environment=order_param[Params.ENV_DICT])


def get_env_var(item_params, egg_vars):
    '''
        Функция смотрит совмещает env variable из egg в pterodactyl'е и их значения из itemparams в billmgr, возвращает словарь
    '''
    env_params = {}
    logger.info(item_params)
    for env in egg_vars:
        env_name = env['attributes']['env_variable']
        if env_name in item_params:
            env_params[env_name] = str(item_params[env_name])
    return env_params

def get_base_pter_domain(item):
    processingmodule_id = misc.get_item_processingmodule(item)
    proccesingparam = misc.get_module_params(processingmodule_id)
    base_url =  proccesingparam['base_url']
    return urlparse(base_url).netloc

def pter_api_key(item):
    '''
        Функция возвращает объект типа PterodactylClient, который инициализирует по параметрам обработчика
    '''
    logger.info("db requests started")
    processingmodule_id = misc.get_item_processingmodule(item)
    proccesingparam = misc.get_module_params(processingmodule_id)
    logger.info("db requests complete")
    api_key = proccesingparam['api_key']
    logger.info("api_key got")
    base_url =  proccesingparam['base_url']
    logger.info("base_url got")
    try:
        pterapi = PterodactylClient(base_url, api_key)
        logger.info("panel inited")
    except Exception as e:
        logger.error(repr(e))
        raise billmgr.exception.XmlException('wrong_panel_info')
    return pterapi

def pter_admin_api_key(item):
    '''
        Функция возвращает объект типа PterodactylClient, который инициализирует по параметрам обработчика
    '''
    logger.info("db requests started")
    processingmodule_id = misc.get_item_processingmodule(item)
    proccesingparam = misc.get_module_params(processingmodule_id)
    logger.info("db requests complete")
    api_key = proccesingparam['admin_api_key']
    logger.info("api_key got")
    base_url =  proccesingparam['base_url']
    logger.info("base_url got")
    try:
        pterapi = PterodactylClient(base_url, api_key)
        logger.info("panel inited")
    except Exception as e:
        logger.error(repr(e))
        raise billmgr.exception.XmlException('wrong_panel_info')

    return pterapi

def user_create(item):
    '''
        Функция создаёт пользователя для услуги на стороне pterodactyl, возвращает id пользователя в pterodactyl
    '''
    pterapi = pter_api_key(item)
    pter_user_id=''
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(20))
    email = get_billaccount_email(item)
    acc_id = get_account_id(item)
    pter_domain = get_base_pter_domain(item)
    username = email.replace('@', '_')
    pter_user_id = pterapi.user.create_user(username=username,
    password=password,
    email=email,
    first_name=str(email),
    last_name=str(email),
    external_id=str(get_account_id(item)))['attributes']['id']
    misc.save_param(item, param='username',value=email)
    misc.save_param(item, param='username_pter',value=f'{pter_domain}/{email}')
    misc.save_param(item, param='userpassword',value=password,crypted=True)
    update_pter_userpassword_with_check(acc_id, password, item)
    return pter_user_id

def get_account_id(item):
    item_info = misc.iteminfo(item)
    return item_info['account_id']

def get_billaccount_email(item):
    acc_id = get_account_id(item)
    return db.db_query('SELECT email FROM user WHERE account=%s ORDER BY id ASC', acc_id)[0]['email']

def get_pteruser_by_item(item):
    pterapi = pter_api_key(item)
    acc_id = get_account_id(item)
    return pterapi.user.get_user_info(external_id=acc_id)['attributes']['id']

def control_server_state(item, state):
    pterapi = pter_api_key(item)
    server_id = pterapi.servers.get_server_info(external_id=item)['uuid']
    pterapi = pter_admin_api_key(item)
    pterapi.client.servers.send_power_action(server_id=server_id, signal=state)

def check_pteruser_exists(item):
    pterapi = pter_api_key(item)
    item_info = misc.iteminfo(item)
    account_id = item_info['account_id']
    try:
        logger.info(pterapi.user.get_user_info(external_id=account_id))
    except Exception as ex:
        return False
    req = get_items_id_from_pter(account_id, item)
    if req:
        for i in req:
            logger.info(f'ip: {i}')
            item_params = misc.itemparams(i)
            logger.info(f'ip: {item_params}')
            if 'username' in item_params and 'userpassword' in item_params:
                return {'username': item_params['username'], 'userpassword': item_params['userpassword']}
    return None

def get_items_id_from_pter(acc_id, item):
    proc_module=misc.get_item_processingmodule(item)
    pter_domain = get_base_pter_domain(item)
    ids=db.db_query_dict('SELECT item FROM itemparam icp JOIN item i ON i.id=icp.item WHERE icp.intname=%(check_field)s AND i.account=%(acc_id)s AND icp.value LIKE %(value)s', check_field='username_pter', acc_id=acc_id, value=f'{pter_domain}%')
    logger.debug(f'request results: {ids}')
    ids_list = []
    for i in ids:
        [ids_list.append(val) for val in i.values()]
    return set(ids_list)

def update_pter_userpassword_with_check(acc_id, password, item):
    items=get_items_id_from_pter(acc_id, item)
    for i in items:
        misc.save_param(i, param='userpassword',value=password,crypted=True)

def random_email():
    '''
        Функция генерирует случайну почту
    '''
    validchars='abcdefghijklmnopqrstuvwxyz1234567890'
    validoms='abcdefghijklmnopqrstuvwxyz'
    login=''
    server=''
    tld=''
    loginlen=random.randint(4,15)
    serverlen=random.randint(3,9)
    tldlen=random.randint(2,3)
    for i in range(loginlen):
        pos=random.randint(0,len(validchars)-1)
        login=login+validchars[pos]
    if login[0].isnumeric():
        pos=random.randint(0,len(validchars)-10)
        login=validchars[pos]+login
    for i in range(serverlen):
        pos=random.randint(0,len(validoms)-1)
        server=server+validoms[pos]
    for i in range(tldlen):
        pos=random.randint(0,len(validoms)-1)
        tld=tld+validoms[pos]
    return login+'@'+server+'.'+tld

def server_create(item, pter_user_id):
    '''
        Функция создаёт сервер на стороне pterodactyl, требует id услуги в billmgr и пользователя в pterodactyl
    '''
    pterapi = pter_api_key(item)
    order_param = order_params(item)
    logger.info("got order parameters")
    response = pterapi.servers.create_server(name=order_param[Params.SERVER_NAME],
                                             user_id=pter_user_id,
                                             nest_id=order_param[Params.NEST_ID],
                                             egg_id=order_param[Params.EGG_ID],
                                             memory_limit=order_param.get(Params.RAM_LIMIT, Params.RAM_LIMIT_DEFAULT),
                                             swap_limit=str(order_param.get(Params.SWAP_LIMIT, Params.SWAP_LIMIT_DEFAULT)),
                                             cpu_limit=str(int(order_param.get(Params.CPU_LIMIT, Params.CPU_LIMIT_DEFAULT))*100),
                                             disk_limit=get_param_from_muliple_keys(order_param,Params.DISK_MEMORY_LIMIT,Params.DISK_MEMORY_LIMIT_DEFAULT),
                                             location_ids=[order_param[Params.LOCATION_ID]],
                                             external_id=str(item),
                                             io_limit=order_param.get(Params.IO_LIMIT, Params.IO_LIMIT_DEFAULT),
                                             backup_limit=order_param.get(Params.BACKUP_LIMIT, Params.BACKUP_LIMIT_DEFAULT),
                                             allocation_limit=order_param.get(Params.ALLOCATION_LIMIT, Params.ALLOCATION_LIMIT_DEFAULT),
                                             database_limit=order_param.get(Params.DB_LIMIT, Params.DB_LIMIT_DEFAULT),
                                             environment=order_param[Params.ENV_DICT])
    logger.info(response)

def get_param_from_muliple_keys(params, keys, default):
    for key in keys:
        if key in params:
            return params[key]
    return default

def order_params(item):
    '''
        Функция собирает содержания, параметры и env var в один словарь order_params
    '''
    item_info = misc.iteminfo(item)
    item_params = misc.itemparams(item)
    addon_params = misc.itemaddons(item)
    pterapi = pter_api_key(item)
    order_param= {}
    # try:
    #     template = item_info['pricelist_intname'].split(';')
    #     for key_val in template:
    #         string = key_val.split("=")
    #         order_param[string[0]]=string[1]
    # except Exception:
    #     logger.info('pricelist template is empty')
    prlparam = misc.get_pricelist_params(item_info['pricelist'])
    order_param[Params.NEST_ID] = prlparam['nest'].replace('nest_','')
    order_param[Params.EGG_ID] = prlparam['egg'].replace('egg_','')
    for param in addon_params:
        order_param[param] = addon_params[param][0]   
    logger.info(f"addon_p: {addon_params}")
    logger.info(f"item_p: {item_params}")

    try:
        server_type = item_params[Params.SERVER_TYPE].split('_')
        logger.extinfo(f'server_type: {item_params[Params.SERVER_TYPE]}')
        order_param[Params.NEST_ID] = server_type[1]
        order_param[Params.EGG_ID] = server_type[0]
    except Exception:
        logger.info('server_type field exception')
    
    order_param[Params.ENV_DICT] = get_env_var(
     item_params, 
     pterapi.nests.get_egg_info(
      egg_id=order_param[Params.EGG_ID],
      nest_id=order_param[Params.NEST_ID], 
      includes={'variables'})['attributes']['relationships']['variables']['data']
    )

    logger.debug(f'env_dict = {order_param[Params.ENV_DICT]}')
    processingmodule_id = misc.get_item_processingmodule(item)
    proccesingparam = misc.get_module_params(processingmodule_id)
    logger.info(proccesingparam)
    if 'pter_location_id' in proccesingparam and proccesingparam['pter_location_id'] != '':
        order_param[Params.LOCATION_ID] = proccesingparam['pter_location_id']


    if not Params.SERVER_NAME in item_params:
        order_param[Params.SERVER_NAME] = str(item)
        misc.save_param(item,param=Params.SERVER_NAME,value=str(item))
    else:
        order_param[Params.SERVER_NAME] = item_params[Params.SERVER_NAME]
        
    return order_param

def get_allocation_id(item,ip,port):
        '''
            Функция возвращает id allocation в pterodactyl
         '''
        pterapi = pter_api_key(item) 
        server = pterapi.servers.get_server_info(external_id=item,includes={'allocations'}) 
        allocations = pterapi.nodes.list_node_allocations(node_id=server['node'])
        alloc_id = None
        for page in allocations:
            for alloc in page:
                if alloc['attributes']['port'] == int(port) and  alloc['attributes']['ip'] == ip:
                    alloc_id = alloc['attributes']['id']
                    break
            if alloc_id:
                break
        
        return alloc_id

def used_ips():
    return db.db_query('SELECT name FROM ip')

def delete_server_ips(item): 
    item_ips = misc.itemips(item)
    private_ips = misc.itemips(item, private_ip=True)
    for ip in item_ips:
        misc.del_ip(ip["id"])
    for ip in private_ips:
        misc.del_ip(ip["id"])
