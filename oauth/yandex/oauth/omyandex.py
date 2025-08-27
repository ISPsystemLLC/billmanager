#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import sys
from urllib import parse

sys.path.insert(0, "/usr/local/mgr5/lib/python")

from billmgr.modules.processing import Module
import billmgr.exception as exc
import billmgr.logger as logging

import requests

logging.init_logging('omyandex')
logger = logging.get_logger('omyandex')

CLIENT_ID = ""
CLIENT_SECRET = ""

mod = Module()

mod.add_argument('--state', type=str, help='state', dest='state')
mod.add_argument('--code', type=str, help='auth code from Yandex', dest='code')
mod.add_argument('--response_type', type=str, help='the name of param with auth code', dest='response_type')
mod.add_argument('--return_url', type=str, help='url for return after authorize', dest='return_url')
mod.add_argument('--from', type=str, help='from', dest='from')
mod.add_argument('--ip', type=str, help='ip', dest='ip')


@mod.command("make_url")
def make_url(state: str, response_type: str, return_url: str):
    params = {
        "return_url": return_url,
        "response_type": response_type,
        "state": state,
        "client_id": CLIENT_ID
    }

    url = f"https://oauth.yandex.ru/authorize?{parse.urlencode(params)}"

    logger.info("URL: '%s'", url)

    doc = ET.Element("doc")
    ET.SubElement(doc, "url").text = url
    ET.dump(doc)


@mod.command("get_user_data")
def get_user_data(code: str, return_url: str):
    logger.info("Try get access token")
    r = requests.post("https://oauth.yandex.ru/token", data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
    })
    logger.info(f"token: {r.text}")
    if not r.ok:
        raise exc.XmlException("token", "error", r.text)
    if "access_token" not in r.json():
        raise exc.XmlException("token", 'missed', "access_token")
    access_token = r.json()["access_token"]

    logger.info("Try get user data")
    r = requests.get("https://login.yandex.ru/info", params={
        "format": "json",
        "oauth_token": access_token,
    })
    logger.info("info: %s", r.text)
    if not r.ok:
        raise exc.XmlException("info", "error", r.text)

    user = r.json()

    doc = ET.Element("doc")
    info = ET.SubElement(doc, "userdata")
    ET.SubElement(info, "id").text = str(user["id"])
    ET.SubElement(info, "email").text = user["default_email"]
    ET.SubElement(info, "realname").text = user["real_name"]
    ET.SubElement(info, "firstname").text = user["first_name"]
    ET.SubElement(info, "lastname").text = user["last_name"]
    ET.dump(doc)


if __name__ == "__main__":
    mod.run()
