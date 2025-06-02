'''
    Точка входа в программу
'''
import commands as cmd
from enum import Enum
import sys
from typing import Dict
sys.path.insert(0, "/usr/local/mgr5/lib/python")
from billmgr.modules.processing import ProcessingModule, Feature
from billmgr.exception import XmlException

import utils.consts as Params
from utils.logger import logger

class ExFeature(Enum):
    '''
        Заглушка для добавление фич не находящихся в billmgr.modules.processing.Feature
    '''
    CHANGE_PASSWORD = 'changepassword'
    SYNC_SERVER = 'sync_server'
    DATACENTER = 'datacenter'
    CHECK_PARAM = 'check_param'
    CHECK_ADDON = 'check_addon'
    REBOOT = 'reboot'


class PydactylModule(ProcessingModule):
    '''
        Реализация billmgr.modules.processing.ProcessingModule
    '''
    def __init__(self) -> None:
        super().__init__(itemtypes=Params.ITEMTYPE)
        self.add_argument("--password", type=str, help="userpassword", dest="password")
        self.add_argument("--userid", type=str, help="userpassword", dest="user_id")
        self.add_argument("--subcommand", type=str, help="subaction", dest='action')
        self.add_argument("--itemtype", type=str, help="itemtype", dest='itemtype')
        self.set_description("Модуль для панели Pterodactyl")
        #self._add_callable_feature(ExFeature.CHECK_PARAM, cmd.import_func('check_param')) - не понятно, когда check_param вызывается

        self._add_callable_feature(Feature.OPEN, cmd.import_func('open_comm'))
        self._add_callable_feature(Feature.CLOSE, cmd.import_func('close'))
        self._add_callable_feature(Feature.RESUME, cmd.import_func('resume'))
        self._add_callable_feature(Feature.SUSPEND, cmd.import_func('suspend'))
        self._add_callable_feature(ExFeature.REBOOT, cmd.import_func('reboot'))
        self._add_callable_feature(Feature.SET_PARAM, cmd.import_func('set_param'))

        self._add_callable_feature(Feature.CHECK_CONNECTION, cmd.import_func('check_connection'))
        self._add_callable_feature(
            Feature.TRANSITION_CONTROL_PANEL, cmd.import_func('transition_control_panel')
        )
        self._add_callable_feature(ExFeature.CHANGE_PASSWORD, cmd.import_func('change_password'))

        # Заказ выделенных IP
        self._add_callable_feature(Feature.IP_ADD, cmd.import_func('add_ip'))
        self._add_callable_feature(Feature.IP_DEL, cmd.import_func('del_ip'))
        self._add_callable_feature(Feature.SYNC_ITEM, cmd.import_func('sync_item'))

        self._add_feature(Feature.PRICELIST_DYNAMIC_SETTINGS)
        self._add_callable_feature(Feature.PRICELIST_DYNAMIC_SETTINGS_TUNE, cmd.import_func('pricelist_dynamic_settings_tune'))


        self._add_feature(ExFeature.DATACENTER)
        #self._add_callable_feature(ExFeature.SYNC_SERVER, cmd.import_func('sync_server'))

    def get_module_param(self) -> Dict[str, Dict[str, str]]:
        '''
            Возвращает набор обязательных параметров,
            которые необходимы при настройке обработчика.
        '''
        return {
            "base_url": {},
            "api_key": {},
            "pter_location_id": {},
            'admin_api_key': {}
        }

    def _on_raise_exception(self, args, err: XmlException) -> None:
        super()._on_raise_exception(args,err)
        logger.extinfo(args)
        sys.stdout.write(err.as_xml())

if __name__ == "__main__":
    logger.extinfo(sys.argv)
    PydactylModule().run()
