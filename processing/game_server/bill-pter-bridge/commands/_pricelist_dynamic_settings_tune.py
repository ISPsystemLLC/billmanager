import xml.etree.ElementTree as ET
from pydactyl import PterodactylClient

import billmgr.session as session
import billmgr.misc as misc

from utils.logger import logger

def pricelist_dynamic_settings_tune(module, itemtype):
    xml = session.get_input_xml()
    proccesingparam = misc.get_module_params(module)
    api_key = proccesingparam['api_key']
    base_url = proccesingparam['base_url']
    pterapi = PterodactylClient(base_url, api_key)
    pages = pterapi.nests.list_nests(includes={'eggs'})
    nests = []
    eggs = []
    for page in pages:
        for nest in page:
            nest_id = f'nest_{nest["attributes"]["id"]}'
            nests.append({'name':nest['attributes']['name'], 'id':nest_id})
            [eggs.append({'name':egg['attributes']['name'], 'id':f'egg_{egg["attributes"]["id"]}', 'depend':nest_id}) for egg in nest['attributes']['relationships']['eggs']['data']]
    
    session.make_slist(
        xml,
       "nest",
        [
            session.SlistElem(
                key=nest['id'], name=nest['name']
            )
            for nest in nests
        ],
    )

    session.make_slist(
        xml,
       "egg",
        [
            session.SlistElem(
                key=egg['id'], name=egg['name'], atributes={"depend": egg['depend']}
            )
            for egg in eggs
        ],
    )
    ET.dump(xml)