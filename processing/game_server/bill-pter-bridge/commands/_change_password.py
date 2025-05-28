'''
    Модуль реализует функцию changepassword .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-changepassword
'''
import billmgr.exception
import billmgr.db as db
import billmgr.misc as misc
import billmgr.crypto as crypto

from utils.misc import pter_api_key
from utils.misc import get_account_id
from utils.misc import update_pter_userpassword_with_check
from utils.misc import get_base_pter_domain
from utils.logger import logger


def change_password(item, password):
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    logger.info("changepassword called")
    api = pter_api_key(item)
    acc_id = get_account_id(item)
    logger.info("panel inited")
    pter_domain = get_base_pter_domain(item)
    users = api.user.list_users(external_id=acc_id)
    if len(users) == 1:
        psw_dec = crypto.decrypt_value(password)
        user_info = users[0]['attributes']
        api.user.edit_user(user_id=user_info['id'],
                           password=psw_dec,
                           username=user_info['username'],
                           email=user_info['email'],
                           first_name=user_info['first_name'],
                           last_name=user_info['last_name'],
                           external_id=user_info['external_id'])
        misc.save_param(iid=item, param='username', value=user_info['username'])
        misc.save_param(item, param='username_pter',value=f'{pter_domain}/{user_info["username"]}')
        misc.save_param(iid=item, param='userpassword', value=psw_dec, crypted=True)
        module = misc.iteminfo(item)['module']
        update_pter_userpassword_with_check(user_info['external_id'], psw_dec, item)
        misc.Mgrctl('service.postchangepassword', elid=item, sok='ok')
    elif len(users) > 1:
        logger.error("collision in external_id")
        raise billmgr.exception.XmlException('collision')
    else:
        logger.error("no user with this id")
        raise billmgr.exception.XmlException('unknown_user')
