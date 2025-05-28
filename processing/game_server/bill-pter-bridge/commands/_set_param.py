'''
    Модуль реализует функцию setparam .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-setparam
'''
import billmgr.misc as misc
import billmgr.exception

from utils.misc import sync_params

def set_param(item, user_id, runningoperation):
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    last_price_list_id = misc.iteminfo(item)['lastpricelist']
    if last_price_list_id is not None:
        #misc.create_manual_task(iid=item,runningoperation=runningoperation,command='setparam') - добавление ручной задачи, 
        #можно вынести в отдельный параметр обработчика
        misc.Mgrctl('service.changepricelist.rollback', elid=item, userid=user_id, sok='ok')
        raise billmgr.exception.XmlException('not_implemented')
    else:
        sync_params(item)
        misc.postsetparam(item)
