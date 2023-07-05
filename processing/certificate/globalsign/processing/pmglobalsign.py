#!/usr/bin/env python3
import sys

sys.path.append("/usr/local/mgr5/lib/python/billmgr/thirdparty")

import warnings
warnings.filterwarnings(action='ignore',message='Python 3.6 is no longer supported')

import argparse
import xml.etree.ElementTree as ET
import datetime
from enum import IntEnum
from typing import List
import socket
import requests
import ipaddress
import os.path
import OpenSSL.crypto
import random
import subprocess
import tempfile

sys.path.insert(0, "/usr/local/mgr5/lib/python")

import billmgr.logger as logging
logging.init_logging("pmglobalsign")
import billmgr.crypto as crypto
import billmgr.misc as misc
import billmgr.db as db
import billmgr.exception as exc

SOAP_ENW = "http://schemas.xmlsoap.org/soap/envelope/"
GS_NAMESPACE = "https://system.globalsign.com/kb/ws/v1/"

TEST_URL = "https://test-gcc.globalsign.com/kb/ws/v1/"
WORKING_URL = "https://system.globalsign.com/kb/ws/v1/"

LOGIN_ERR_CODE = "-4001"

DAYS_AUTODELETE_AFTER_ISSUED = 6
DAYS_AUTODELETE_AFTER_ORDER = 30

SERVICE_ORDER_ID = "custom_order_id"
SERVICE_STATUS_ADDITION = "service_status_addition"


class CertificateStatus(IntEnum):
    IS_REQUESTED = 3
    IS_ENROLLED = 4
    IS_ISSUED = 5
    IS_FAILED = 6


logger = logging.get_logger("pmglobalsign")


class Status(IntEnum):
    INITIAL = 1
    WAITING_FOR_PHISHING_CHECK = 2
    CANCELLED_NOT_ISSUED = 3
    ISSUED = 4
    CANCELLED_ISSUED = 5
    WAITING_FOR_REVOCATION = 6
    REVOKED = 7


def check_ip(ip):
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return False
    else:
        return True


def session_for_src_addr(addr) -> requests.Session:
    session = requests.Session()
    for prefix in ("http://", "https://"):
        session.get_adapter(prefix).init_poolmanager(
            connections=requests.adapters.DEFAULT_POOLSIZE,
            maxsize=requests.adapters.DEFAULT_POOLSIZE,
            source_address=(addr, 0),
        )

    return session


def register_namespace(node: ET.Element, prefix: str, url: str):
    node.attrib["xmlns:" + prefix] = url


def replace(data: str, rp: dict):
    for word, initial in rp.items():
        data = data.replace(word.lower(), initial)
    return data


def get_subjects(cert):
    fix_name = {
        "commonName": "CN",
        "countryName": "C",
        "organizationName": "O",
        "localityName": "L",
    }
    subjects = {}
    for subject in cert.subject:
        subjects[fix_name.get(subject.oid._name, subject.oid._name)] = subject.value
    return subjects


def get_certificates(self) -> List[crypto.x509.Certificate]:
    from OpenSSL.crypto import _lib, _ffi, X509

    certs = _ffi.NULL
    if self.type_is_signed():
        certs = self._pkcs7.d.sign.cert
    elif self.type_is_signedAndEnveloped():
        certs = self._pkcs7.d.signed_and_enveloped.cert

    pycerts = []
    for i in range(_lib.sk_X509_num(certs)):
        pycert = X509.__new__(X509)
        pycert._x509 = _lib.X509_dup(_lib.sk_X509_value(certs, i))
        pycerts.append(pycert.to_cryptography())

    if not pycerts:
        return None
    return pycerts


def get_SAN_option_type(cn: str, alt_name: str):
    if check_ip(alt_name):
        if (
                alt_name.find("10.") == 0
                or alt_name.find("192.168.") == 0
                or (
                alt_name.find("172.") == 0
                and (int(alt_name[4:2]) > 15 or int(alt_name[4:2]) < 32)
        )
        ):
            return "4"
        return "3"
    else:
        if alt_name.endswith("." + cn):
            uc_prefix = {"www", "owa", "mail", "autodiscover"}
            domain = alt_name.split(".")
            if domain[0] in uc_prefix and domain[1] == cn:
                return "1"
            return "2"
        elif alt_name.split(".")[0] == "*":
            return "13"
        return "7"


class Api:
    class RequestMethod(IntEnum):
        POST = (1,)
        GET = 2

    def __init__(self, module: int, params: dict = None):
        if params:
            self.__module_params = params
        else:
            self.__module_params = misc.get_module_params(module)
        self.order_id = ""

    def request(
            self,
            method: str,
            header: dict = None,
            request: str = "",
            r_method: RequestMethod = RequestMethod.GET,
    ):
        logger.debug("Make api call. request:\n%s", request)

        session = requests.Session()
        if self.__module_params["sourceip"] and check_ip(
                self.__module_params["sourceip"]
        ):
            session = session_for_src_addr(self.__module_params["sourceip"])
        session.headers.update(header)
        url = TEST_URL if self.__module_params["usedemo"] == "on" else WORKING_URL
        url += method

        if r_method == self.RequestMethod.GET:
            response = session.get(url)
        elif r_method == self.RequestMethod.POST:
            response = session.post(url, data=request)
        else:
            raise exc.XmlException("response")

        logger.debug("response:%s", response.content)
        response_xml = ET.fromstring(response.content)
        success_code = response_xml.find(".//SuccessCode")
        if (
                success_code != None
                and success_code.text != "0"
                and success_code.text != "1"
        ):
            err_msg = response_xml.find(".//ErrorMessage")

            if err_msg != None:
                logger.debug("error_message %s", err_msg.text)
                err_code = response_xml.find(".//ErrorCode")
                if err_code.text != LOGIN_ERR_CODE:
                    raise exc.XmlException(
                        "api_error", err_object="", err_value=err_msg.text
                    )

        return response_xml

    def set_request_header(self, type: str = "Order", ns: str = ""):
        request_header = ET.Element(ns + type + "RequestHeader")
        auth_token = ET.SubElement(request_header, ns + "AuthToken")
        username = ET.SubElement(auth_token, ns + "UserName")
        username.text = self.__module_params["username"]
        password = ET.SubElement(auth_token, ns + "Password")
        password.text = self.__module_params["password"]

        return request_header

    def get_DV_approverlist(self, domain: str):
        logger.debug("Get DV approverlist")

        envelope = ET.Element("SOAP-ENV:Envelope")
        register_namespace(envelope, "SOAP-ENV", SOAP_ENW)
        register_namespace(envelope, "ns1", GS_NAMESPACE)
        body = ET.SubElement(envelope, "SOAP-ENV:Body")
        ns1 = ET.SubElement(body, "ns1:GetDVApproverList")
        request = ET.SubElement(ns1, "Request")
        fqdn = ET.SubElement(request, "FQDN")
        fqdn.text = domain

        request.append(self.set_request_header("Query"))

        response = self.request(
            "ServerSSLService",
            {"Content-Type": "text/xml"},
            ET.tostring(envelope),
            Api.RequestMethod.POST,
        )

        result = []
        for approver in response.findall(".//ApproverEmail"):
            result.append(approver.text)

        xpath = response.find(".//OrderID")
        if xpath != None:
            self.order_id = xpath.text

        return result


class GlobalSign:
    def __init__(self, iid, module: int = None, renew: bool = False):
        self.__load_item_params(iid, module)

        self.iid = iid
        self.processingmodule = self.__iteminfo.get("processingmodule")
        self.__module_params = misc.get_module_params(self.processingmodule)
        self.renew = renew

    def __load_item_params(self, iid: int, module: int = None):
        self.__iteminfo = misc.iteminfo(iid)
        self.__item_params = misc.itemparams(iid)
        csr = db.get_first_record(
            "SELECT csr " "FROM certificate " "WHERE item = %s", iid
        )

        if csr:
            self.__item_params.update(get_subjects(crypto.x509decode(csr["csr"])))
            self.__item_params["csr"] = csr["csr"]

        if module is not None and self.__iteminfo["processingmodule"] is None:
            self.__iteminfo["processingmodule"] = module
        self.__module_params = misc.get_module_params(
            int(self.__iteminfo["processingmodule"])
        )

    def set_org_info(self):
        org_info = ET.Element("OrganizationInfo")
        name = ET.SubElement(org_info, "OrganizationName")
        name.text = self.__item_params["org_name"]
        duns = ET.SubElement(org_info, "OrganizationCode")
        duns.text = self.__item_params.get("org_duns")
        address = ET.SubElement(org_info, "OrganizationAddress")
        address1 = ET.SubElement(address, "AddressLine1")
        address1.text = self.__item_params["org_address"]
        ET.SubElement(address, "AddressLine2")
        ET.SubElement(address, "AddressLine3")
        city = ET.SubElement(address, "City")
        city.text = self.__item_params["org_city"]
        retion = ET.SubElement(address, "Region")
        retion.text = self.__item_params["org_state"]
        postalcode = ET.SubElement(address, "PostalCode")
        postalcode.text = self.__item_params["org_postcode"]
        country = ET.SubElement(address, "Country")
        country.text = self.__item_params["C"]
        phone = ET.SubElement(address, "Phone")
        phone.text = self.__item_params["org_phone"]

        return org_info

    def set_org_info_EV(self):
        org_info_ev = ET.Element("OrganizationInfoEV")
        name = ET.SubElement(org_info_ev, "BusinessAssumedName")
        name.text = self.__item_params["org_name"]
        duns = ET.SubElement(org_info_ev, "OrganizationCode")
        duns.text = self.__item_params.get("org_duns")
        code = ET.SubElement(org_info_ev, "BusinessCategoryCode")
        code.text = "BE"
        address = ET.SubElement(org_info_ev, "OrganizationAddress")
        address1 = ET.SubElement(address, "AddressLine1")
        address1.text = self.__item_params["org_address"]
        ET.SubElement(address, "AddressLine2")
        ET.SubElement(address, "AddressLine3")
        city = ET.SubElement(address, "City")
        city.text = self.__item_params["org_city"]
        region = ET.SubElement(address, "Region")
        region.text = self.__item_params["org_state"]
        postalcode = ET.SubElement(address, "PostalCode")
        postalcode.text = self.__item_params["org_postcode"]
        country = ET.SubElement(address, "Country")
        country.text = self.__item_params["C"]
        phone = ET.SubElement(address, "Phone")
        phone.text = self.__item_params["org_phone"]
        fax = ET.SubElement(address, "Fax")
        fax.text = self.__item_params["org_phone"]

        return org_info_ev

    def set_authorized_signer_info(self):
        auth_signer_info = ET.Element("AuthorizedSignerInfo")
        name = ET.SubElement(auth_signer_info, "OrganizationName")
        name.text = self.__item_params["org_name"]
        first_name = ET.SubElement(auth_signer_info, "FirstName")
        first_name.text = self.__item_params["adm_fname"]
        last_name = ET.SubElement(auth_signer_info, "LastName")
        last_name.text = self.__item_params["adm_lname"]
        function = ET.SubElement(auth_signer_info, "Function")
        function.text = self.__item_params["adm_jtitle"]
        phone = ET.SubElement(auth_signer_info, "Phone")
        phone.text = self.__item_params["adm_phone"]
        email = ET.SubElement(auth_signer_info, "Email")
        email.text = self.__item_params["adm_email"]

        return auth_signer_info

    def set_contact_info(self):
        contact_info = ET.Element("ContactInfo")
        email = ET.SubElement(contact_info, "Email")
        email.text = self.__item_params["adm_email"]
        first_name = ET.SubElement(contact_info, "FirstName")
        first_name.text = self.__item_params["adm_fname"]
        last_name = ET.SubElement(contact_info, "LastName")
        last_name.text = self.__item_params["adm_lname"]
        phone = ET.SubElement(contact_info, "Phone")
        phone.text = self.__item_params["adm_phone"]

        return contact_info

    def set_second_contact_info(self):
        second_contact_info = ET.Element("SecondContactInfo")
        email = ET.SubElement(second_contact_info, "Email")
        email.text = self.__item_params["adm_email"]
        first_name = ET.SubElement(second_contact_info, "FirstName")
        first_name.text = self.__item_params["adm_fname"]
        last_name = ET.SubElement(second_contact_info, "LastName")
        last_name.text = self.__item_params["adm_lname"]

        return second_contact_info

    def set_jurisdiction_info(self):
        jurisdiction_info = ET.Element("JurisdictionInfo")
        country = ET.SubElement(jurisdiction_info, "JurisdictionCountry")
        country.text = self.__item_params["C"]
        region = ET.SubElement(jurisdiction_info, "StateOrProvince")
        region.text = self.__item_params["org_state"]
        city = ET.SubElement(jurisdiction_info, "Locality")
        city.text = self.__item_params["L"]
        crn = ET.SubElement(jurisdiction_info, "IncorporationAgencyRegistrationNumber")
        crn.text = "004655432"

        return jurisdiction_info

    def set_approver_info(self):
        approver_info = ET.Element("ApproverInfo")
        email = ET.SubElement(approver_info, "Email")
        email.text = self.__item_params["adm_email"]
        first_name = ET.SubElement(approver_info, "FirstName")
        first_name.text = self.__item_params["adm_fname"]
        function = ET.SubElement(approver_info, "Function")
        function.text = self.__item_params["adm_jtitle"]
        last_name = ET.SubElement(approver_info, "LastName")
        last_name.text = self.__item_params["adm_lname"]
        name = ET.SubElement(approver_info, "OrganizationName")
        name.text = self.__item_params["org_name"]
        ET.SubElement(approver_info, "OrganizationUnit")
        phone = ET.SubElement(approver_info, "Phone")
        phone.text = self.__item_params["adm_phone"]

        return approver_info

    def set_requestor_info(self):
        set_requestor_info = ET.Element("RequestorInfo")
        email = ET.SubElement(set_requestor_info, "Email")
        email.text = self.__item_params["adm_email"]
        first_name = ET.SubElement(set_requestor_info, "FirstName")
        first_name.text = self.__item_params["adm_fname"]
        function = ET.SubElement(set_requestor_info, "Function")
        function.text = self.__item_params["adm_jtitle"]
        last_name = ET.SubElement(set_requestor_info, "LastName")
        last_name.text = self.__item_params["adm_lname"]
        name = ET.SubElement(set_requestor_info, "OrganizationName")
        name.text = self.__item_params["org_name"]
        unit = ET.SubElement(set_requestor_info, "OrganizationUnit")
        unit.text = (
            self.__item_params["OU"]
            if self.__item_params.get("OU")
            else self.__module_params["default_OU"]
        )
        phone = ET.SubElement(set_requestor_info, "Phone")
        phone.text = self.__item_params["adm_phone"]

        return set_requestor_info

    def set_order_request_parameter(self, order: bool = False, ns: str = ""):
        type = self.__iteminfo["pricelist_intname"]
        wildcard = False
        if (
                self.__item_params["CN"][0] == "*"
                or self.__iteminfo["pricelist_intname"].find("_wild") != -1
        ):
            wildcard = True
        if (
                self.__module_params["usedemo"] == "on"
                and order
                and self.__iteminfo["pricelist_intname"].find("EV") == -1
        ):
            type = "TEST_" + type

        order_request_param = ET.Element(ns + "OrderRequestParameter")
        type = order_type_dns(type, self.__item_params["approver_method"], wildcard)
        product_code = ET.SubElement(order_request_param, ns + "ProductCode")
        product_code.text = get_valid_product_type(type)
        if wildcard:
            base_option = ET.SubElement(order_request_param, ns + "BaseOption")
            base_option.text = "wildcard"
        order_kind = ET.SubElement(order_request_param, ns + "OrderKind")
        order_kind.text = "renewal" if self.renew else "new"
        licenses = ET.SubElement(order_request_param, ns + "Licenses")
        licenses.text = "1"

        if not ns:
            san = self.__item_params["altname"].split()
            if san:
                options = ET.SubElement(order_request_param, "Options")
                option = ET.SubElement(options, "Option")
                option_name = ET.SubElement(option, "OptionName")
                option_name.text = "SAN"
                option_value = ET.SubElement(option, "OptionValue")
                option_value.text = "true"

        validity_period = ET.SubElement(order_request_param, ns + "ValidityPeriod")
        months = ET.SubElement(validity_period, ns + "Months")
        months.text = str(self.__iteminfo["period"])
        csr = ET.SubElement(order_request_param, ns + "CSR")
        csr.text = self.__item_params["csr"]

        if self.renew:
            renewal_target_order_ID = ET.SubElement(
                order_request_param, ns + "RenewalTargetOrderID"
            )
            renewal_target_order_ID.text = self.__item_params[SERVICE_ORDER_ID]

        return order_request_param

    def validate_order_parametrs(self):
        logger.debug("Validate Order Parameters")
        validate_order = ET.Element("SOAP-ENV:Envelope")
        register_namespace(validate_order, "SOAP-ENV", SOAP_ENW)
        register_namespace(validate_order, "ns1", GS_NAMESPACE)
        body = ET.SubElement(validate_order, "SOAP-ENV:Body")
        validate_order_parameters = ET.SubElement(body, "ns1:ValidateOrderParameters")
        request = ET.SubElement(validate_order_parameters, "Request")
        api = Api(self.processingmodule)
        request.append(api.set_request_header())
        request.append(self.set_order_request_parameter())

        response = api.request(
            "GASService",
            {"Content-Type": "text/xml"},
            ET.tostring(validate_order),
            Api.RequestMethod.POST,
        )
        validate_response(response)

    def validate_order_parametrs_old(self, order: bool = False):
        logger.debug("Validate Order Parameters Old")
        validate_order = ET.Element("SOAP-ENV:Envelope")
        register_namespace(validate_order, "SOAP-ENV", SOAP_ENW)
        register_namespace(
            validate_order, "ns1", "http://stub.order.gasapiserver.esp.globalsign.com"
        )
        body = ET.SubElement(validate_order, "SOAP-ENV:Body")
        validate_order_parameters = ET.SubElement(body, "ns1:GSValidateOrderParameters")
        request = ET.SubElement(validate_order_parameters, "ns1:Request")
        api = Api(self.processingmodule)
        request.append(api.set_request_header(ns="ns1:"))
        request.append(self.set_order_request_parameter(ns="ns1:"))

        response = api.request(
            "GasOrder",
            {"SOAPaction": "ValidateOrderParameters"},
            ET.tostring(validate_order),
            Api.RequestMethod.POST,
        )
        validate_response(response, GS_NAMESPACE)

    def get_order_status(self):
        logger.debug("Get Order By Order ID")
        order = ET.Element("SOAP-ENV:Envelope")
        register_namespace(order, "SOAP-ENV", SOAP_ENW)
        register_namespace(
            order, "ns1", "http://stub.query.gasapiserver.esp.globalsign.com"
        )
        body = ET.SubElement(order, "SOAP-ENV:Body")
        order_by_order_id = ET.SubElement(body, "ns1:GetOrderByOrderID")
        request = ET.SubElement(order_by_order_id, "Request")
        api = Api(self.processingmodule)
        request.append(api.set_request_header("Query"))
        order_id = ET.SubElement(request, "OrderID")
        order_id.text = self.__item_params[SERVICE_ORDER_ID]

        options = ET.SubElement(request, "OrderQueryOption")
        status = ET.SubElement(options, "OrderStatus")
        status.text = "1"
        return_certificate_info = ET.SubElement(options, "ReturnCertificateInfo")
        return_certificate_info.text = "true"
        return_fullfillment = ET.SubElement(options, "ReturnFulfillment")
        return_fullfillment.text = "true"

        response = api.request(
            "GASService",
            {"Content-Type": "text/xml"},
            ET.tostring(order),
            Api.RequestMethod.POST,
        )
        validate_response(response)

        return response

    def validate_status(self):
        response = self.get_order_status()
        order_status = int(response.find(".//OrderStatus").text)
        certificate_status = int(response.find(".//CertificateStatus").text)

        cancelled = order_status in {
            Status.CANCELLED_NOT_ISSUED,
            Status.CANCELLED_ISSUED,
            Status.WAITING_FOR_REVOCATION,
            Status.REVOKED,
        } or certificate_status in {
                        Status.CANCELLED_NOT_ISSUED,
                        Status.CANCELLED_ISSUED,
                        Status.WAITING_FOR_REVOCATION,
                        Status.REVOKED,
                    }

        logger.debug(
            "Order status: %d, certificate Status: %d", order_status, certificate_status
        )

        if self.__item_params.get(SERVICE_STATUS_ADDITION) == "check" and (
                order_status != Status.WAITING_FOR_PHISHING_CHECK
                or cancelled
                or certificate_status != Status.INITIAL
        ):
            misc.drop_param(self.iid, SERVICE_STATUS_ADDITION)
            self.__item_params.pop(SERVICE_STATUS_ADDITION)

        if not cancelled and certificate_status == Status.INITIAL:
            misc.set_service_status(self.iid, CertificateStatus.IS_ENROLLED)
            if (
                    order_status == Status.WAITING_FOR_PHISHING_CHECK
                    and self.__item_params.get(SERVICE_STATUS_ADDITION) != "check"
            ):
                misc.save_param(self.iid, SERVICE_STATUS_ADDITION, "check")
        elif not cancelled and certificate_status == Status.ISSUED:
            end_date = response.find(".//EndDate").text.split("T")[0]

            misc.set_service_expiredate(self.iid, end_date)
            misc.set_service_status(self.iid, CertificateStatus.IS_ISSUED)

            xpath_crt = response.find(".//X509Cert")
            crt = xpath_crt.text if xpath_crt != None else ""

            xpath_pkcs7 = response.find(".//PKCS7Cert")
            pkcs7 = xpath_pkcs7.text if xpath_pkcs7 != None else ""

            rm = {"*": "_", ".": "_"}

            files = {}
            if pkcs7:
                files[
                    os.path.normpath(replace(self.__item_params["CN"], rm)) + ".p7b"
                    ] = pkcs7
                certs = get_certificates(
                    OpenSSL.crypto.load_pkcs7_data(OpenSSL.crypto.FILETYPE_PEM, pkcs7)
                )
                for cert in certs:
                    subjects = get_subjects(cert)
                    if "CN" in subjects:
                        name = subjects["CN"]
                    elif "O" in subjects:
                        name = subjects["O"]
                    else:
                        name = bytes(random.randrange(0, 255) for i in range(8)).hex()
                    files[
                        os.path.normpath(replace(name, rm)) + ".crt"
                        ] = OpenSSL.crypto.dump_certificate(
                        OpenSSL.crypto.FILETYPE_PEM, cert
                    ).decode()
            if files:
                zip_dir = tempfile.TemporaryDirectory(
                    prefix="zip_", dir="/usr/local/mgr5/tmp"
                )
                archive_file_name = (
                        os.path.normpath(replace(self.__item_params["CN"], rm)) + ".zip"
                )
                archive_name = os.path.normpath(
                    os.path.join(zip_dir.name, archive_file_name)
                )
                cmd = ["zip", archive_file_name]
                for file in files:
                    my_file = open(
                        os.path.normpath(os.path.join(zip_dir.name, file)), "w"
                    )
                    my_file.write(files[file])
                    my_file.close()
                    cmd.append(file)
                process = subprocess.run(cmd, cwd=zip_dir.name)
                if process.returncode == 0:
                    my_file = open(archive_name, "rb")
                    misc.Mgrctl(
                        "certificate.save",
                        elid=self.iid,
                        crt=crypto.base64encode(my_file.read()),
                        crt_type="zip",
                        sok="ok",
                    )
                else:
                    files.clear()

            if not files and crt:
                misc.Mgrctl("certificate.save", elid=self.iid, crt=crt, sok="ok")
        elif cancelled:
            misc.Mgrctl("certificate.failed", elid=self.iid, sok="ok")
            misc.set_service_status(self.iid, CertificateStatus.IS_FAILED)

    def validate_csr(self):
        logger.debug("Validate CSR")
        validate_csr = ET.Element("SOAP-ENV:Envelope")
        register_namespace(validate_csr, "SOAP-ENV", SOAP_ENW)
        register_namespace(validate_csr, "ns1", GS_NAMESPACE)
        body = ET.SubElement(validate_csr, "SOAP-ENV:Body")
        decode_csr = ET.SubElement(body, "DecodeCSR")
        request = ET.SubElement(decode_csr, "Request")
        api = Api(self.processingmodule)
        request.append(api.set_request_header("Query"))
        csr = ET.SubElement(request, "CSR")
        csr.text = self.__item_params["csr"]
        product_type = ET.SubElement(request, "ProductType")
        product_type.text = get_valid_product_type(self.__iteminfo["pricelist_intname"])

        api.request(
            "GASService",
            {"Content-Type": "text/xml"},
            ET.tostring(validate_csr),
            Api.RequestMethod.POST,
        )

    def process_order(self):
        logger.debug("Order")
        self.validate_csr()
        self.validate_order_parametrs_old()

        logger.debug("IntName: %s", self.__iteminfo["pricelist_intname"])
        dv_cert = (
                self.__iteminfo["pricelist_intname"].find("DV") != -1
                or self.__iteminfo["pricelist_intname"].find("DV_LOW") != -1
        )
        approver_method_email = (
                not self.__item_params["approver_method"]
                or self.__item_params["approver_method"] == "auth_email"
        )
        api = Api(self.processingmodule)
        order_type = ""

        if dv_cert:
            if approver_method_email:
                order_type += "DVOrder"
                api.get_DV_approverlist(self.__item_params["CN"])
            elif self.__item_params["approver_method"] == "auth_dnstxt":
                order_type += "DVDNSOrder"
        elif self.__iteminfo["pricelist_intname"].find("OV") != -1:
            order_type += "OVOrder"
        elif self.__iteminfo["pricelist_intname"].find("EV") != -1:
            order_type += "EVOrder"

        order = ET.Element("SOAP-ENV:Envelope")
        register_namespace(order, "SOAP-ENV", SOAP_ENW)
        register_namespace(order, "ns1", GS_NAMESPACE)
        body = ET.SubElement(order, "SOAP-ENV:Body")
        order_type = ET.SubElement(body, order_type)
        request = ET.SubElement(order_type, "Request")
        request.append(api.set_request_header())
        request.append(self.set_order_request_parameter())

        if dv_cert:
            order_id_node = ET.SubElement(request, "OrderID")
            order_id_node.text = api.order_id
            if approver_method_email:
                approver = self.__item_params["approver_email"].split(",")
                approver_email_node = ET.SubElement(request, "ApproverEmail")
                approver_email_node.text = approver[0]

        if self.__iteminfo["pricelist_intname"].find("OV") != -1:
            request.append(self.set_org_info())
        elif self.__iteminfo["pricelist_intname"].find("EV") != -1:
            request.append(self.set_org_info_EV())
            request.append(self.set_requestor_info())
            request.append(self.set_approver_info())

        if self.__iteminfo["pricelist_intname"].find("EV") != -1:
            request.append(self.set_authorized_signer_info())
            request.append(self.set_jurisdiction_info())

        request.append(self.set_contact_info())

        if self.__iteminfo["pricelist_intname"].find("DV") != -1:
            request.append(self.set_second_contact_info())

        san_entries = ET.SubElement(request, "SANEntries")
        if self.__item_params["altname"]:
            san = self.__item_params["altname"].split(" ")
            for s in san:
                san_entry = ET.SubElement(san_entries, "SANEntry")
                option_type = ET.SubElement(san_entry, "SANOptionType")
                option_type.text = get_SAN_option_type(self.__item_params["CN"], s)
                subject_altname = ET.SubElement(san_entry, "SubjectAltName")
                subject_altname.text = s

        response = api.request(
            "ServerSSLService",
            {"Content-Type": "text/xml"},
            ET.tostring(order),
            Api.RequestMethod.POST,
        )
        validate_response(response)
        for xpath in response.findall(".//OrderID") + response.findall(".//OrderId"):
            if xpath != None:
                self.__item_params[SERVICE_ORDER_ID] = xpath.text
        misc.save_param(
            self.iid, SERVICE_ORDER_ID, self.__item_params[SERVICE_ORDER_ID]
        )

        if self.__item_params["approver_method"] == "auth_dnstxt":
            misc.save_param(
                self.iid,
                self.__item_params["approver_method"] + "_value",
                response.find(".//DNSTXT").text,
                )
            domains = ""
            for VerificationFQDN in response.findall(
                    ".//VerificationFQDNList/VerificationFQDN"
            ):
                if domains:
                    domains += ","
                domains += VerificationFQDN.text
            misc.save_param(self.iid, "domains_list", domains)

        try:
            misc.set_service_status(self.iid, CertificateStatus.IS_REQUESTED)
            self.validate_status()
        except Exception as err:
            logger.warning("%s", err)

    def close_cert(self):
        response = self.get_order_status()
        order_date_str = response.find(".//OrderDate").text.split("T")[0]
        order_date = datetime.datetime.strptime(order_date_str, "%Y-%m-%d").date()
        start_date_str = response.find(".//StartDate").text
        if start_date_str:
            start_date = datetime.datetime.strptime(
                start_date_str.split("T")[0], "%Y-%m-%d"
            ).date()
        else:
            start_date = datetime.date.today()
        order_status = int(response.find(".//OrderStatus").text)
        certificate_status = int(response.find(".//CertificateStatus").text)
        cancelled = order_status in {
            Status.CANCELLED_NOT_ISSUED,
            Status.CANCELLED_ISSUED,
            Status.WAITING_FOR_REVOCATION,
            Status.REVOKED,
        } or certificate_status in {
                        Status.CANCELLED_NOT_ISSUED,
                        Status.CANCELLED_ISSUED,
                        Status.WAITING_FOR_REVOCATION,
                        Status.REVOKED,
                    }
        not_issued = order_status in {
            Status.INITIAL,
            Status.WAITING_FOR_PHISHING_CHECK,
        } or certificate_status in {Status.INITIAL, Status.WAITING_FOR_PHISHING_CHECK}

        if not cancelled and (
                (
                        certificate_status == Status.ISSUED
                        and start_date + datetime.timedelta(days=DAYS_AUTODELETE_AFTER_ISSUED)
                        >= datetime.date.today()
                )
                or (
                        not_issued
                        and order_date_str
                        and order_date + datetime.timedelta(days=DAYS_AUTODELETE_AFTER_ORDER)
                        >= datetime.date.today()
                )
        ):
            modify_order = ET.Element("SOAP-ENV:Envelope")
            register_namespace(modify_order, "SOAP-ENV", SOAP_ENW)
            register_namespace(
                modify_order, "ns1", "http://stub.order.gasapiserver.esp.globalsign.com"
            )
            body = ET.SubElement(modify_order, "SOAP-ENV:Body")
            order = ET.SubElement(body, "ns1:ModifyOrder")
            request = ET.SubElement(order, "Request")
            api = Api(self.processingmodule)
            request.append(api.set_request_header())

            order_id = ET.SubElement(request, "OrderID")
            order_id.text = self.__item_params[SERVICE_ORDER_ID]
            order_operation = ET.SubElement(request, "ModifyOrderOperation")
            order_operation.text = "CANCEL"

            response = api.request(
                "ServerSSLService",
                {"Content-Type": "text/xml"},
                ET.tostring(modify_order),
                Api.RequestMethod.POST,
            )
            validate_response(response)

    def reopen(self):
        reopen_order = ET.Element("SOAP-ENV:Envelope")
        register_namespace(reopen_order, "SOAP-ENV", SOAP_ENW)
        register_namespace(reopen_order, "ns1", GS_NAMESPACE)
        body = ET.SubElement(reopen_order, "SOAP-ENV:Body")
        reissue = ET.SubElement(body, "ReIssue")
        request = ET.SubElement(reissue, "Request")
        api = Api(self.processingmodule)
        request.append(api.set_request_header())

        order_parameter = ET.SubElement(request, "OrderParameter")
        csr = ET.SubElement(order_parameter, "CSR")
        csr.text = self.__item_params["csr"]
        ET.SubElement(order_parameter, "DNSNames")
        order_id = ET.SubElement(request, "TargetOrderID")
        order_id.text = self.__item_params[SERVICE_ORDER_ID]
        ET.SubElement(request, "HashAlgorithm")

        response = api.request(
            "GASService",
            {"Content-Type": "text/xml"},
            ET.tostring(reopen_order),
            Api.RequestMethod.POST,
        )
        misc.postreopen(self.iid)
        misc.set_service_status(self.iid, CertificateStatus.IS_REQUESTED)

        self.__item_params[SERVICE_ORDER_ID] = response.find(".//OrderID").text
        misc.save_param(
            self.iid, SERVICE_ORDER_ID, self.__item_params[SERVICE_ORDER_ID]
        )

    def validate_domain_by_DNS(self, domain: str):
        req = ET.Element("SOAP-ENV:Envelope")
        register_namespace(req, "SOAP-ENV", SOAP_ENW)
        register_namespace(req, "ns2", "https://system.globalsign.com/bb/ws/")
        body = ET.SubElement(req, "SOAP-ENV:Body")
        dvdns_verify = ET.SubElement(body, "ns2:DVDNSVerificationForIssue")
        request = ET.SubElement(dvdns_verify, "Request")
        api = Api(self.processingmodule)
        request.append(api.set_request_header())

        order_id = ET.SubElement(request, "OrderID")
        order_id.text = self.__item_params[SERVICE_ORDER_ID]
        approver = ET.SubElement(request, "ApproverFQDN")
        approver.text = domain

        response = api.request(
            "ServerSSLService",
            {"Content-Type": "text/xml"},
            ET.tostring(req),
            Api.RequestMethod.POST,
        )
        validate_response(response)

        try:
            self.validate_status()
        except Exception as err:
            logger.warning("%s", err)

    def validate_domain_by_email(self, emails: List[str]):
        approver_method_email = (
                self.__item_params["approver_method"]
                or self.__item_params["approver_method"] == "auth_email"
        )

        if not approver_method_email:
            logger.warning("No action, approver method is not 'auth_email'")
            return

        req = ET.Element("SOAP-ENV:Envelope")
        register_namespace(req, "SOAP-ENV", SOAP_ENW)
        body = ET.SubElement(req, "SOAP-ENV:Body")
        approver = ET.SubElement(body, "ChangeApproverEmail")
        request = ET.SubElement(approver, "Request")
        api = Api(self.processingmodule)
        request.append(api.set_request_header())

        order_id = ET.SubElement(request, "OrderID")
        order_id.text = self.__item_params[SERVICE_ORDER_ID]
        approver = ET.SubElement(request, "ApproverEmail")
        approver.text = emails[0].strip()
        fqdn = ET.SubElement(request, "FQDN")
        fqdn.text = self.__item_params["CN"]

        response = api.request(
            "ServerSSLService",
            {"Content-Type": "text/xml"},
            ET.tostring(req),
            Api.RequestMethod.POST,
        )
        validate_response(response)
        misc.save_param(self.iid, "approver_email", ",".join(emails))


def get_valid_product_type(intname: str):
    if intname.find("_wild") != -1:
        return intname.replace("_wild", "")
    return intname


def order_type_dns(type: str, approver_method: str, wildcard: bool):
    if approver_method == "auth_dnstxt" and type.find("DV") != -1:
        res = ""
        if type.find("DV_LOW") != -1:
            res = "DV_LOW"
        else:
            res = "DV_HIGH"
        res += "_DNS"
        if wildcard:
            res += "_wild"
        return res
    return type


def build_error_msg(errors: ET.Element):
    error_msg = ""
    for error in errors:
        error_msg += "ErrorCode: " + error.get("ErrorCode") + ", "
        "ErrorField: " + error.get("ErrorField") + ", "
        "ErrorMessage: " + error.get("ErrorMessage") + "\n"

    return error_msg.strip()


def build_fatal_error_msg(faults: ET.Element):
    faults_msg = ""
    for fault in faults:
        faults_msg += (
                fault.find("faultcode").text + ": " + fault.find("faultstring").text + "\n"
        )

    return faults_msg.strip()


def validate_response(res: ET.Element, url_xml: str = ""):
    xpath = (
        res.find(".//ns:SuccessCode", {"ns": url_xml})
        if url_xml
        else res.find(".//SuccessCode")
    )
    code = 0

    if xpath != None:
        code = xpath.text

    if code == -1:
        errors = (
            res.findall(".//ns:Error", {"ns": url_xml})
            if url_xml
            else res.findall(".//Error")
        )
        raise exc.XmlException(build_error_msg(errors))

    faults = res.findall("./soap:Envelope/soap:Body/soap:Fault", {"soap": SOAP_ENW})
    if faults:
        raise exc.XmlException(build_fatal_error_msg(faults))


def features():
    doc = ET.Element("doc")

    itemtypes = ET.SubElement(doc, "itemtypes")
    ET.SubElement(itemtypes, "itemtype").set("name", "certificate")

    params = ET.SubElement(doc, "params")
    ET.SubElement(params, "param").set("name", "username")
    password = ET.SubElement(params, "param")
    password.set("name", "password")
    password.set("crypted", "yes")
    ET.SubElement(params, "param").set("name", "usedemo")
    ET.SubElement(params, "param").set("name", "sourceip")
    ET.SubElement(params, "param").set("name", "alter_approver_methods")
    ET.SubElement(params, "param").set("name", "threshold")
    customparam = ET.SubElement(params, "customparam")
    customparam.set("name", "default_OU")
    customparam.set("unique", "yes")
    customparam.set("defval", "IT")

    features_node = ET.SubElement(doc, "features")
    ET.SubElement(features_node, "feature").set("name", "check_connection")
    ET.SubElement(features_node, "feature").set("name", "prolong")
    ET.SubElement(features_node, "feature").set("name", "sync_item")
    ET.SubElement(features_node, "feature").set("name", "tune_connection")
    ET.SubElement(features_node, "feature").set("name", "approver")
    ET.SubElement(features_node, "feature").set("name", "send_dv_dns")
    ET.SubElement(features_node, "feature").set("name", "send_dv_email")

    templates_node = ET.SubElement(doc, "templates")
    dv_low = ET.SubElement(templates_node, "template")
    dv_low.set("id", "DV_LOW")
    dv_low.set("authemail", "yes")
    dv_low.set("authdnstxt", "yes")
    dv_low_wild = ET.SubElement(templates_node, "template")
    dv_low_wild.set("id", "DV_LOW_wild")
    dv_low_wild.set("wildcard", "yes")
    dv_low_wild.set("authemail", "yes")
    dv_low_wild.set("authdnstxt", "yes")
    dv = ET.SubElement(templates_node, "template")
    dv.set("id", "DV")
    dv.set("multidomain", "yes")
    dv.set("authemail", "yes")
    dv.set("authdnstxt", "yes")
    dv_wild = ET.SubElement(templates_node, "template")
    dv_wild.set("id", "DV_wild")
    dv_wild.set("wildcard", "yes")
    dv_wild.set("authemail", "yes")
    dv_wild.set("authdnstxt", "yes")
    ov = ET.SubElement(templates_node, "template")
    ov.set("id", "OV")
    ov.set("multidomain", "yes")
    ov.set("orginfo", "yes")
    ov_wild = ET.SubElement(templates_node, "template")
    ov_wild.set("id", "OV_wild")
    ov_wild.set("wildcard", "yes")
    ov_wild.set("orginfo", "yes")
    ev = ET.SubElement(templates_node, "template")
    ev.set("id", "EV")
    ev.set("multidomain", "yes")
    ev.set("orginfo", "yes")

    ET.dump(doc)


def check_connection(xml):
    logger.debug("Check connection")
    params = xml.find("processingmodule")

    envelope = ET.Element("SOAP-ENV:Envelope")
    register_namespace(envelope, "SOAP-ENV", SOAP_ENW)
    register_namespace(envelope, "ns1", GS_NAMESPACE)
    body = ET.SubElement(envelope, "SOAP-ENV:Body")
    ns1 = ET.SubElement(body, "ns1:AccountSnapshot")
    request = ET.SubElement(ns1, "Request")

    param_dict = {
        "usedemo": params.find("usedemo").text,
        "username": params.find("username").text,
        "password": params.find("password").text,
    }
    sourceip = params.find("sourceip")
    if sourceip != None:
        param_dict["sourceip"] = sourceip.text

    api = Api(
        params.find("id").text,
        param_dict,
    )
    request.append(api.set_request_header("Query"))

    logger.debug("Check connection: %s", ET.tostring(envelope))

    response = api.request(
        "AccountService",
        {"Content-Type": "text/xml"},
        ET.tostring(envelope),
        Api.RequestMethod.POST,
    )
    error_code = response.find(".//ErrorCode")
    if error_code != None and error_code.text == LOGIN_ERR_CODE:
        raise exc.XmlException("invalid_login_or_passwd")


def open_item(item):
    logger.debug("Request new certificate for item %d", item)
    gs = GlobalSign(item)
    gs.process_order()
    misc.Mgrctl("certificate.open", elid=item, sok="ok")


def prolong(item):
    logger.debug("Request prolong certificate for item %d", item)
    gs = GlobalSign(item, renew=True)
    gs.process_order()
    misc.postprolong(item)


def resume(item):
    misc.postresume(item)


def suspend(item):
    misc.postsuspend(item)


def close_item(item):
    gs = GlobalSign(item)
    gs.close_cert()
    misc.postclose(item)


def sync_item(item):
    gs = GlobalSign(item)
    gs.validate_status()


def reopen(item):
    gs = GlobalSign(item)
    gs.reopen()


def approver(module, domain: str):
    domains = domain.split(",")
    approver = ET.Element("doc")
    api = Api(module)
    for dom in domains:
        dom_node = ET.SubElement(approver, "domain")
        dom_node.set("name", dom)
        approver_list = api.get_DV_approverlist(dom)
        for email in approver_list:
            approver_node = ET.SubElement(dom_node, "approver")
            approver_node.text = email

    return approver


def send_dv_dns(item, domain: str):
    gs = GlobalSign(item)
    gs.validate_domain_by_DNS(domain)


def send_dv_email(item, email: str):
    emails = email.split(",")
    gs = GlobalSign(item)
    gs.validate_domain_by_email(emails)


def tune_connection():
    logger.debug("Tune connection")

    xml = ET.fromstring(sys.stdin.read())
    slist = ET.SubElement(xml, "slist")
    slist.set("name", "sourceip")
    null_elem = ET.SubElement(slist, "msg")
    null_elem.text = "null"
    null_elem.set("key", "")
    logger.debug("Input: %s", ET.tostring(xml))

    for addr in socket.gethostbyname_ex(socket.gethostname())[-1]:
        elem = ET.SubElement(slist, "msg")
        elem.text = addr
        elem.set("key", addr)

    ET.dump(xml)


def get_args():
    parser = argparse.ArgumentParser(description="Processing virtual servers")
    parser.add_argument("--command", type=str, help="command name", dest="command")
    parser.add_argument(
        "--item", type=int, help="item the command is related to", dest="item"
    )
    parser.add_argument(
        "--module", type=int, help="module the command is related to", dest="module"
    )
    parser.add_argument(
        "--runningoperation",
        type=int,
        help="related runningoperation",
        dest="runningoperation",
    )
    parser.add_argument(
        "--domain", type=str, help="domain name for ssl certificate", dest="domain"
    )
    parser.add_argument("--emails", type=str, help="emails for approve", dest="emails")
    args, _ = parser.parse_known_args()
    logger.info("Args: %s", args)

    return args


def process_command():
    args = get_args()
    try:
        if args.command == "features":
            features()

        elif args.command == "check_connection":
            check_connection(ET.fromstring(sys.stdin.read()))

        elif args.command == "open":
            open_item(args.item)

        elif args.command == "prolong":
            prolong(args.item)

        elif args.command == "resume":
            resume(args.item)

        elif args.command == "suspend":
            suspend(args.item)

        elif args.command == "close":
            close_item(args.item)

        elif args.command == "sync_item":
            sync_item(args.item)

        elif args.command == "reopen":
            reopen(args.item)

        elif args.command == "approver":
            approver(args.module, args.domain)

        elif args.command == "send_dv_dns":
            send_dv_dns(args.item, args.domain)

        elif args.command == "send_dv_email":
            send_dv_email(args.item, args.emails)

        elif args.command == "tune_connection":
            tune_connection()

        else:
            raise exc.XmlException("unknown command", "", args.command)

        logger.extinfo("Command finished")

    except Exception as err:
        exc.log_backtrace()
        # Фиксируем ошибку в интерфейсе
        if isinstance(err, exc.XmlException):
            xml_err = err
        else:
            xml_err = exc.XmlException(err_type=args.command, err_value=str(err))
        if args.runningoperation:
            misc.save_runningoperation_error(
                args.runningoperation, xml_err.as_module_error()
            )
        else:
            print(xml_err.as_xml())

        sys.exit(1)


if __name__ == "__main__":
    process_command()
