"""
    Инит модуля, включает в себя подключение комманд
"""

import importlib


def import_func(module_name, entry_point=None):
    """
    Функция, которая непосредственно выполняет подключение комманды
    """
    module_to_imp = importlib.import_module(f"commands._{module_name}")
    return getattr(module_to_imp, entry_point if entry_point else module_name)
