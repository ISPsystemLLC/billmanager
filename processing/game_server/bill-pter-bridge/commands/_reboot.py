from utils.misc import control_server_state
import billmgr.misc as misc


def reboot(item):
    control_server_state(item, 'restart')
    misc.postreboot(item)
