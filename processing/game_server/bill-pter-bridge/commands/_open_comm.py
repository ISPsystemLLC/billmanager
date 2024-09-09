'''
    Модуль реализует функцию open .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-open
'''
import billmgr.misc as misc
import time
import secrets
import string

from utils.logger import logger
import utils.consts as Params
from utils.misc import pter_api_key
from utils.misc import server_create
from utils.misc import user_create
from utils.misc import get_pteruser_by_item
from utils.misc import check_pteruser_exists
from utils.misc import get_base_pter_domain
from utils.misc import get_account_id
from utils.misc import control_server_state

def open_comm(item: int) -> None:
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    logger.info(f"open command started")
    pterapi = pter_api_key(item)
    pter_domain = get_base_pter_domain(item)
    # 1.Создание пользователя
    with misc.FileLock(f'tmp/.tmp/{"pter_user_create_".join(str(get_account_id(item)))}'):
        collision_user = check_pteruser_exists(item)
        logger.info(f"test: {collision_user}")
        new_acc_flag = False
        if collision_user:
            misc.save_param(item, param='username',value=collision_user['username'])
            misc.save_param(item, param='username_pter',value=f'{pter_domain}/{collision_user["username"]}')
            misc.save_param(item, param='userpassword',value=collision_user['userpassword'],crypted=True)
            user_id = get_pteruser_by_item(item)
        elif collision_user is not None:
            user_id = user_create(item)
            new_acc_flag = True
        else:
            user_id = get_pteruser_by_item(item)
            user_info = pterapi.user.get_user_info(user_id=user_id)['attributes']
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(20))
            pterapi.user.edit_user(user_id=user_id,
            username=user_info['username'],
            password=password,
            email=user_info['email'],
            first_name=user_info['first_name'],
            last_name=user_info['last_name'],
            external_id=user_info['external_id'])
            misc.save_param(item, param='username',value=user_info['email'])
            misc.save_param(item, param='username_pter',value=f'{pter_domain}/{user_info["email"]}')
            misc.save_param(item, param='userpassword',value=password,crypted=True)
    # 2.Создание сервера/ получение существующего сервера
    server_info = None
    try:
        server_info = pterapi.servers.get_server_info(external_id=item, includes={'allocations'})
    except:
        server_create(item, user_id)
    # 3.Вычитывание параметров, которые нужно отдать биллингу
    if not server_info:
        server_info = pterapi.servers.get_server_info(external_id=item, includes={'allocations'})
    ip = server_info['relationships']['allocations']['data'][0]['attributes']['ip']
    port = server_info['relationships']['allocations']['data'][0]['attributes']['port']
    misc.save_param(item,param=Params.SERVER_ID,value=server_info['id'])
    ## Получаем список всех слотов под IP
    conditions = [("ip.status=%s", [1])]
    ips = misc.itemips(item, conditions)
    if ips:
        misc.commit_ip(ip_id=misc.save_ip(ip_id=ips[0]["id"], ip=f"{ip}:{port}", domain=''))

    #4.Ожидание старта сервера
    for i in range(Params.START_RETRY_COUNT):
        try:
            logger.info(f"Trying start server {item} ... {i}")
            control_server_state(item, 'start')
            break
        except Exception as e:
            logger.warning(f"Can't start server {e}. Restart")
        time.sleep(Params.TIME_WAIT_BETWEEN_START_TRY)

    #5.postopen
    try:    
        misc.postopen(item, ip=f"{ip}:{port}", address=f"{ip}:{port}")
    except:
        misc.postopen(item)

