import billmgr.session as session
import billmgr.misc as misc
import xml.etree.ElementTree as ET
from utils.consts import PICKLE_PATH
from pmnextcloud import LOGGER


def pricelist_dynamic_settings_tune(module):
    xml = session.get_input_xml()
    LOGGER.info(f"Unpickle preset for module {module}")
    usergroups = [""]
    try:
        usergroups = misc.unpickle(PICKLE_PATH + f"/module_preset_{module}")
    except Exception as e:
        LOGGER.error(f"Can't unpickle {e}")
    session.make_slist(
        xml,
        "usergroup",
        [
            session.SlistElem(key=usergroup.index(usergroup), name=usergroup)
            for usergroup in usergroups
        ],
    )
    ET.dump(xml)
