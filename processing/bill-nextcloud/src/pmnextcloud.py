#!/usr/bin/python3
"""
    Точка входа в программу
"""
import sys
import os

sys.path.append("/usr/local/mgr5/lib/python")
from billmgr.modules.processing import ProcessingModule, Feature
from billmgr.exception import XmlException
import billmgr.logger as logging
import utils.consts as Params
import commands as cmd
from typing import Dict
from enum import Enum

logging.init_logging("pmnextcloud")
LOGGER = logging.get_logger("pmnextcloud")


class NextcloudModule(ProcessingModule):
    """
    Реализация billmgr.modules.processing.ProcessingModule
    """

    def __init__(self) -> None:
        super().__init__(itemtypes=Params.ITEMTYPE)
        self.add_argument("--password", type=str, help="userpassword", dest="password")
        self.add_argument("--userid", type=str, help="userid", dest="user_id")
        self.add_argument("--subcommand", type=str, help="subaction", dest="action")
        self.add_argument("--itemtype", type=str, help="itemtype", dest="itemtype")
        # self.add_argument("--module", type=str, help="module", dest="module")
        self.set_description("Модуль для панели NextCloud")

        self._add_callable_feature(
            Feature.CHECK_CONNECTION, cmd.import_func("check_connection")
        )
        self._add_callable_feature(Feature.OPEN, cmd.import_func("open"))
        self._add_callable_feature(Feature.CLOSE, cmd.import_func("close"))
        self._add_callable_feature(Feature.RESUME, cmd.import_func("resume"))
        self._add_callable_feature(Feature.SUSPEND, cmd.import_func("suspend"))
        self._add_callable_feature(Feature.SET_PARAM, cmd.import_func("set_param"))
        self._add_callable_feature(Feature.STAT, cmd.import_func("stat"))
        self._add_callable_feature(
            Feature.GET_SERVER_CONFIG, cmd.import_func("get_config")
        )
        self._add_callable_feature(
            Feature.PRICELIST_DYNAMIC_SETTINGS_TUNE,
            cmd.import_func("pricelist_dynamic_settings_tune"),
        )
        self._add_feature(Feature.PRICELIST_DYNAMIC_SETTINGS)

        self._add_callable_feature(
            Feature.CONNECTION_FORM_TUNE, cmd.import_func("tune_connection")
        )

    def get_module_param(self) -> Dict[str, Dict[str, str]]:
        """
        Возвращает набор обязательных параметров,
        которые необходимы при настройке обработчика.
        """
        return {"base_url": {}, "nc_username": {}, "nc_password": {}}

    def _on_raise_exception(self, args, err: XmlException) -> None:
        super()._on_raise_exception(args, err)
        LOGGER.extinfo(args)
        sys.stdout.write(err.as_xml())


def is_running_in_venv():
    return sys.prefix != sys.base_prefix


if __name__ == "__main__":
    if not is_running_in_venv():
        real_path = os.path.realpath(__file__)
        real_dir = os.path.dirname(real_path)
        VENV_PATH = os.path.abspath(
            os.path.join(real_dir, "..", "venv-nextcloud", "bin", "python")
        )
        if not os.path.isfile(VENV_PATH) or not os.access(VENV_PATH, os.X_OK):
            print(
                f"Error: Python interpreter not found or not executable at {VENV_PATH}",
                file=sys.stderr,
            )
            sys.exit(1)
        os.execv(VENV_PATH, [VENV_PATH] + sys.argv)

    LOGGER.extinfo(sys.argv)
    NextcloudModule().run()
