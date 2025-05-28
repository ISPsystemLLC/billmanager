'''
    Модуль реализует функцию transition_control_panel .
    https://www.ispsystem.ru/docs/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-obrabotki#id-Созданиемодулейобработки-transition_controlpanel
'''
import sys
from urllib.parse import urljoin

import billmgr.misc as misc
from utils.logger import logger

def transition_control_panel(item, panelkey):
    '''
        Точка входа для импорта, именуется так же как модуль
    '''
    logger.info("db requests started")
    processingparam = ''
    if not panelkey:
        proccesingparam = misc.get_module_params(misc.get_item_processingmodule(item))
    else:
        proccesingparam = misc.get_module_params(panelkey)
    logger.info("db requests complete")
    base_url = proccesingparam['base_url']
    logger.info("base_url got")
    sys.stdout.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<doc>
  <url>{urljoin(base_url, '/auth/login')}</url>
  <panelcount>1</panelcount>
  <panelname keyname="pter">pterodactyl</panelname>
</doc>
''')
   