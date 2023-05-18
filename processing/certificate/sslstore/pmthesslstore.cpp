#include <mgr/mgrrpc.h>
#include <ispbin.h>
#include "defines.h"
#include "sslutil.h"
#include "util.h"
#include "module.h"

using namespace processing;
using namespace opts;
using namespace std;

#define BINARY_NAME "pmthesslstore"

MODULE(BINARY_NAME);
  
class Certificate : public Module {
public:
	Certificate(const string& name);
	virtual bool AllowChooseServer() { return false; }
protected:
	virtual CertificateModuleArgs* MakeModuleArgs();
	virtual int GetMaxTryCount(const std::string &operation);
	virtual void InternalAddItemParam(StringMap &params, const int iid);
private:
	virtual void ProcessCommand();
	void SetParam(const int iid);
};

Certificate::Certificate(const string& name): Module(name) {}

void Certificate::ProcessCommand() {
	auto c_m_args = dynamic_cast<CertificateModuleArgs*>(m_args.get());
	if (c_m_args->Command.AsString() == PROCESSING_CERTIFICATE_APPROVER)
	{
		try {
			std::cout << ApproverList(str::Int(c_m_args->Module), c_m_args->Domain, c_m_args->IntName).Str(true);
		} catch (...) {
			throw mgr_err::Error(PROCESSING_CERTIFICATE_APPROVER);
		}
	}
}

void Certificate::SetParam(const int iid) {
	sbin::ClientQuery("func=service.postsetparam&sok=ok&elid=" + str::Str(iid));
}

int Certificate::GetMaxTryCount(const std::string &operation) {
	if (operation == PROCESSING_PROLONG)
		return 1;
	return Module::GetMaxTryCount(operation);
}

void Certificate::InternalAddItemParam(StringMap &params, const int iid) {
	mgr_db::QueryPtr param = sbin::DB()->Query("SELECT pkey, csr, crt FROM certificate WHERE item = " + str::Str(iid));
	if (!param->Eof()) {
		params["key"] = param->AsString("pkey");
		params["csr"] = param->AsString("csr");
		params["crt"] = param->AsString("crt");
	}
}

CertificateModuleArgs* Certificate::MakeModuleArgs() {
	return new CertificateModuleArgs();
}

class TheSSLStore : public Certificate {
private:
	StringMap item_params;
	
	string url;
	string partner_code;
	string auth_token;

public:
	TheSSLStore(): Certificate	(BINARY_NAME) {}

	mgr_xml::Xml Features() {
		mgr_xml::Xml xml;
		// Опредаляем тип продукта для обработчика
		auto itemtypes = xml.GetRoot().AppendChild("itemtypes");
		itemtypes.AppendChild("itemtype").SetProp("name", "certificate");

		// Определяем список параметров которые необходимо сохранить при добавлении обработчика
		auto params = xml.GetRoot().AppendChild("params");
		params.AppendChild("param").SetProp("name", "url");
		params.AppendChild("param").SetProp("name", "auth_token").SetProp("crypted", "yes"); // Хранить auth_token в зашифрованом виде
		params.AppendChild("param").SetProp("name", "partner_code");

		// Определяем список поддерживаемых возможностей обработчика
		auto features = xml.GetRoot().AppendChild("features");
		features.AppendChild("feature").SetProp("name", PROCESSING_CHECK_CONNECTION); 		// Проверяем соединение при подключении обработчика
		features.AppendChild("feature").SetProp("name", PROCESSING_CERTIFICATE_APPROVER);	// Получать список approver_email от регистратора
		features.AppendChild("feature").SetProp("name", PROCESSING_PROLONG);				// Поддерживает продление сертификатов
		features.AppendChild("feature").SetProp("name", PROCESSING_USERCREATE);				// Поддерживает создание польователя SSL-регистратора на втором шаге визарда
		features.AppendChild("feature").SetProp("name", PROCESSING_SYNC_ITEM);				// Поддерживает синхронизацию услуг

		// Добавляем шаблоны сертификатов регистратора TheSSLStore
		// Подробное описание шаблонов сертификатов находится по адресу https://www.thesslstore.com/api/product-codes
		auto templates = xml.GetRoot().AppendChild("templates");
		// SYMANTEC
		templates.AppendChild("template").SetProp("name", "securesiteproev").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "securesiteev").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "securesitepro").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "securesite").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "securesitewildcard").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		// GEOTRUST
		templates.AppendChild("template").SetProp("name", "quicksslpremium").SetProp(TEMPLATE_WWW, "yes");
		templates.AppendChild("template").SetProp("name", "quicksslpremiummd").SetProp(TEMPLATE_WWW, "yes").SetProp(TEMPLATE_MULTIDOMAIN, "yes");
		templates.AppendChild("template").SetProp("name", "truebusinessidev").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "truebizid").SetProp(TEMPLATE_ORGINFO, "yes").SetProp(TEMPLATE_CSRALTNAME, "yes");
		templates.AppendChild("template").SetProp("name", "truebizidmd").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes").SetProp(TEMPLATE_CSRALTNAME, "yes");
		templates.AppendChild("template").SetProp("name", "truebusinessidwildcard").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "truebusinessidevmd").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		// THAWTE
		templates.AppendChild("template").SetProp("name", "sslwebserverev").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "sslwebserver").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "sslwebserverwildcard").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "ssl123").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "sgcsupercerts").SetProp(TEMPLATE_ORGINFO, "yes");
		// RAPIDSSL
		templates.AppendChild("template").SetProp("name", "rapidssl");
		templates.AppendChild("template").SetProp("name", "rapidsslwildcard").SetProp(TEMPLATE_WILDCARD, "yes");
		templates.AppendChild("template").SetProp("name", "freessl");
		// COMODO
		templates.AppendChild("template").SetProp("name", "essentialssl").SetProp(TEMPLATE_WWW, "yes");
		templates.AppendChild("template").SetProp("name", "essentialwildcard").SetProp(TEMPLATE_WILDCARD, "yes");
		templates.AppendChild("template").SetProp("name", "instantssl").SetProp(TEMPLATE_WWW, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "instantsslpro").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodoevssl").SetProp(TEMPLATE_WWW, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodomdc").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodosgc").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodosgcwildcard").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodossl").SetProp(TEMPLATE_WWW, "yes");
		templates.AppendChild("template").SetProp("name", "comodopremiumssl").SetProp(TEMPLATE_WWW, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodoevmdc").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodoucc").SetProp(TEMPLATE_MULTIDOMAIN, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comododvucc").SetProp(TEMPLATE_MULTIDOMAIN, "yes");
		templates.AppendChild("template").SetProp("name", "comodowildcard").SetProp(TEMPLATE_WILDCARD, "yes");
		templates.AppendChild("template").SetProp("name", "comodoevsgc").SetProp(TEMPLATE_WWW, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodopremiumwildcard").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "comodouccwildcard").SetProp(TEMPLATE_ORGINFO, "yes").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_MULTIDOMAIN, "yes");
		templates.AppendChild("template").SetProp("name", "elitessl").SetProp(TEMPLATE_WWW, "yes").SetProp(TEMPLATE_ORGINFO, "yes"); 
		templates.AppendChild("template").SetProp("name", "positivessl");
		templates.AppendChild("template").SetProp("name", "positivemdcssl").SetProp(TEMPLATE_MULTIDOMAIN, "yes");
		templates.AppendChild("template").SetProp("name", "positivesslwildcard").SetProp(TEMPLATE_WILDCARD, "yes");
		templates.AppendChild("template").SetProp("name", "positivemdcwildcard").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_MULTIDOMAIN, "yes");
		// CERTUM
		templates.AppendChild("template").SetProp("name", "ucommercialssl").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "ucommercialwildcard").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "utrustedssl").SetProp(TEMPLATE_ORGINFO, "yes");
		templates.AppendChild("template").SetProp("name", "utrustedwildcard").SetProp(TEMPLATE_WILDCARD, "yes").SetProp(TEMPLATE_ORGINFO, "yes");
		
		return xml;
	}

	/**
	 * @brief Способы отправки запроса
	 */
	enum request_method {
		  POST	= 1
		, GET	= 2
	};

	/**
	 * @brief Отправляем запрос к API регистратора
	 * @param [in] service имя сервиса.
	 * @param [in] method метод.
	 * @param [in] request запрос.
	 * @param [in] request_method способ отправки запроса GET/POST.
	 * @return ответ регистратора в формате XML
	 */
	mgr_xml::Xml ApiRequest(const string& service, const string& method, string request = "", request_method r_method = GET) {
		STrace();
		str::inpl::Trim(request);
		Debug("Make api call. Service: %s, method: %s, request:\n%s", service.c_str(), method.c_str(), request.c_str());
		
		mgr_rpc::HttpQuery http;
		http.EnableCookie();
		http.AcceptAnyResponse();
		http.AddHeader("Content-Type: text/xml");
		std::stringstream output;
		switch (r_method) {
			case POST:
				http.Post(url + service + (method.empty() ? "" : "/") + method, request, output);
				break;
			case GET:
				http.Get(url + service + "/" + method, output);
				break;
			default:
				throw mgr_err::Value("request", "r_method");
		}
		
		Debug("Api response: %s", output.str().c_str());

		mgr_xml::XmlString api_out(output.str());

		// Обработаем ошибку
		if (api_out.GetNode("//isError").Str() == "true") {
			string error_message;
			ForEachI(api_out.GetNodes("//Message/string"), e) {
				error_message += e->Str()  + "\n";
			}
			
			str::inpl::Trim(error_message);
			
			Debug("error_message: %s", error_message.c_str());

			// Выбросим исключение если возникла ошибка
			throw mgr_err::Error("api_error").add_message("response", error_message);
		}
		
		return api_out;
	}

	/**
	 * @brief Приводит TheSSLStore::url в формат <protocol>://<domain>/rest/
	 */
	void ValidateUrl()
	{
		string protocol;
		
		Debug("Validate url: %s", url.c_str());
		
		if (url.find("://") != string::npos) {
			protocol = url.substr(0, url.find("://"));
			str::GetWord(url, "://");
		} else {
			protocol = "https";
		}
		
		Debug("Protocol: %s", protocol.c_str());
		Debug("Result url: %s", url.c_str());
		
		string domain;
		if (url.find("/") != string::npos) {
			domain = str::GetWord(url, "/");
		} else {
			domain = url;
		}
		
		if (domain.empty())
			throw mgr_err::Value("processing", "url");
		
		url = protocol + "://" + domain + "/rest/";
		
		Debug("Result url: %s", url.c_str());
	}

	/**
	 * @brief Проверяет статус сервисов TheSSLStore
	 */
	void ValidateApi()
	{
		ApiRequest("health", "status");
	}

	/**
	 * @brief Производит проверку авторизации TheSSLStore
	 */
	void ValidateAuth()
	{
		mgr_xml::Xml request;
		request.SetRoot("AuthRequest");
		request.GetRoot().AppendChild("PartnerCode", partner_code);
		request.GetRoot().AppendChild("AuthToken", auth_token);
		
		ApiRequest("health", "validate", request.Str(true), POST);
	}

	/**
	 * @brief Заполняет авторизационные данные
	 * @param [in] request XML запроса к TheSSLStore
	 */
	void SetAuth(mgr_xml::Xml& request) {
		mgr_xml::XmlNode auth = request.GetRoot().AppendChild("AuthRequest");
		auth.AppendChild("PartnerCode", partner_code);
		auth.AppendChild("AuthToken", auth_token);
	}	

	/**
	 * @brief Заполняет данные организации
	 * @param [in] request XML запроса к TheSSLStore
	 */
	void SetOrgInfo(mgr_xml::Xml& request) {
		mgr_xml::XmlNode auth = request.GetRoot().AppendChild("OrganisationInfo");
		auth.AppendChild("OrganizationName", item_params["org_name"]);
		auth.AppendChild("DUNS", item_params["org_duns"]);
		auth.AppendChild("Division", item_params["org_division"]);
		auth.AppendChild("IncorporatingAgency", item_params["org_incorporating_agency"]);
		auth.AppendChild("RegistrationNumber", item_params["org_registration_number"]);
		auth.AppendChild("JurisdictionCity", item_params["org_city"]);
		auth.AppendChild("JurisdictionRegion", item_params["org_state"]);
		auth.AppendChild("JurisdictionCountry", item_params["C"]);
		mgr_xml::XmlNode address = auth.AppendChild("OrganizationAddress");
		address.AppendChild("AddressLine1", item_params["org_address"]);
		address.AppendChild("AddressLine2");
		address.AppendChild("AddressLine3");
		address.AppendChild("City", item_params["org_city"]);
		address.AppendChild("Region", item_params["org_state"]);
		address.AppendChild("PostalCode", item_params["org_postcode"]);
		address.AppendChild("Country", item_params["C"]);
		address.AppendChild("Phone", item_params["org_phone"]);
		address.AppendChild("Fax", item_params["org_phone"]);
		address.AppendChild("LocalityName", item_params["L"]);
	}	

	/**
	 * @brief Заполняет данные контакта сертификата
	 * @param [in] request XML запроса к TheSSLStore
	 * @param [in] contact_prefix префикс контакта сертификата
	 */
	void SetContactInfo(mgr_xml::XmlNode& contact, const string& contact_prefix) {
		contact.AppendChild("FirstName", item_params[contact_prefix + "fname"]);
		contact.AppendChild("LastName", item_params[contact_prefix + "lname"]);
		contact.AppendChild("Phone", item_params[contact_prefix + "phone"]);
		contact.AppendChild("Fax", item_params["org_phone"]);
		contact.AppendChild("Email", item_params[contact_prefix + "email"]);
		contact.AppendChild("Title", item_params[contact_prefix + "jtitle"]);
		contact.AppendChild("OrganizationName", item_params["org_name"]);
		contact.AppendChild("AddressLine1", item_params["org_address"]);
		contact.AppendChild("AddressLine2");
		contact.AppendChild("City", item_params["org_city"]);
		contact.AppendChild("Region", item_params["org_state"]);
		contact.AppendChild("PostalCode", item_params["org_postcode"]);
		contact.AppendChild("Country", item_params["C"]);
	}

	/**
	 * @brief Заполняет данные Адмнинистративного и Технического контактов
	 * @param [in] request XML запроса к TheSSLStore
	 */
	void SetContactInfo(mgr_xml::Xml& request) {
		mgr_xml::XmlNode admin = request.GetRoot().AppendChild("AdminContact");
		SetContactInfo(admin, "adm_");
		mgr_xml::XmlNode tech = request.GetRoot().AppendChild("TechnicalContact");
		SetContactInfo(tech, "tech_");
	}

	/**
	 * @brief Проверяет корректность CSR запроса
	 * @param [in] product код сертификата
	 * @param [in] csr CSR запрос
	 */
	void ValidateCSR(const string& product, const string& csr) {
		mgr_xml::Xml request;
		request.SetRoot("CSRRequest");
		SetAuth(request);
		request.GetRoot().AppendChild("ProductCode", product);
		request.GetRoot().AppendChild("CSR", csr);
		
		ApiRequest("csr", "", request.Str(true), POST);
	}

	/**
	 * @brief Заполняет параметры сертификата
	 * @param [in] iid код услуги
	 */
	void Init(const int iid) {
		static bool initialized = false;
		if (initialized) return;

		AddItemParam(item_params, iid);
		if (item_params.find("csr") == item_params.end())
			throw mgr_err::Value("certificate", "csr");

		// Получаем параметры CSR запроса
		auto csr = mgr_crypto::x509::DecodeRequest(item_params["csr"]);
		ForEachI(csr.GetSubject(), s) {
			item_params[s->first] = s->second;
		}

		auto item_query = ItemQuery(iid);
		
		for (size_t i = 0; i < item_query->ColCount(); ++i) {
			item_params[item_query->ColName(i)] = item_query->AsString(i);
		}
		
		SetModule(str::Int(item_params["processingmodule"]));
		
		initialized = true;
	}

	/**
	 * @brief Заполняет параметры модуля обработки и проверяет корректность полученных данных
	 * @param [in] module ID модуля обработки
	 */
	virtual void OnSetModule(const int module) 
	{
		url = m_module_data["url"];
		partner_code = m_module_data["partner_code"];
		auth_token = m_module_data["auth_token"];
		
		ValidateUrl();
		ValidateApi();
		ValidateAuth();
	}

	/**
	 * @brief Проверяет подключение к сервисам TheSSLStore
	 * @param [in] module_xml XML с параметрами подключения
	 */
	void CheckConnection(mgr_xml::Xml module_xml)
	{
		url = module_xml.GetNode("/doc/processingmodule/url").Str();
		partner_code = module_xml.GetNode("/doc/processingmodule/partner_code").Str();
		auth_token = module_xml.GetNode("/doc/processingmodule/auth_token").Str();
		
		ValidateUrl();
		ValidateApi();
		ValidateAuth();
	}

	/**
	 * @brief Открытие услуги
	 * @param [in] iid id услуги
	 */
	void Open(const int iid)
	{
		Debug("Request new certificate for item %d", iid);
		ProcessOrder(iid);
		sbin::ClientQuery("func=service.postopen&sok=ok&elid=" + str::Str(iid));
	}

	/**
	 * @brief Продление услуги
	 * @param [in] iid id услуги
	 */
	void Prolong(const int iid)
	{
		Debug("Request prolong certificate for item %d", iid);
		ProcessOrder(iid, true);
	}

	/**
	 * @brief Обработка услуги
	 * @param [in] iid id услуги
	 * @param [in] renew проблить
	 */
	void ProcessOrder(const int iid, bool renew = false)
	{
		Init(iid);
		ValidateCSR(item_params["pricelist_intname"], item_params["csr"]);
		
		string custom_id = util::RandomString(16);
		
		mgr_xml::Xml request;
		request.SetRoot("NewOrderRequest");
		SetAuth(request);
		request.GetRoot().AppendChild("CustomOrderID", custom_id);
		request.GetRoot().AppendChild("ProductCode", item_params["pricelist_intname"]);
		SetOrgInfo(request);
		request.GetRoot().AppendChild("ValidityPeriod", item_params["period"]);
		request.GetRoot().AppendChild("ServerCount", "1");
		request.GetRoot().AppendChild("CSR", item_params["csr"]);
		request.GetRoot().AppendChild("DomainName", item_params["CN"]);
		request.GetRoot().AppendChild("WebServerType", "other");
		auto dns_names = request.GetRoot().AppendChild("DNSNames");
		
		string approver_email = item_params["approver_email"];
		string approver_domain = approver_email;
		str::GetWord(approver_domain, "@");

		StringList san;
		str::Split(item_params[CERTIFICATE_ALTNAME], san, " ");
		ForEachI(san, s) {
			dns_names.AppendChild("string", *s);
			
			if (item_params["pricelist_intname"].find("comodo") == 0) {
				if (s->find(approver_domain) == s->size() - approver_domain.size()) {
					str::inpl::Append(approver_email, item_params["approver_email"], ",");
				} else {
					str::Append(approver_email, "none", ",");
				}
			}
		}
		
		request.GetRoot().AppendChild("isRenewalOrder", renew ? "true" : "false");
		SetContactInfo(request);
		
		request.GetRoot().AppendChild("ApproverEmail", approver_email);
		request.GetRoot().AppendChild("ReserveSANCount", str::Str(ssl_util::OrderedAltNamesCount(sbin::DB(), iid)));
		request.GetRoot().AppendChild("AddInstallationSupport", "false");
		request.GetRoot().AppendChild("EmailLanguageCode", "EN");
		
		mgr_xml::Xml response = ApiRequest("order", "neworder", request.Str(true), POST);
		
		if (renew) sbin::ClientQuery("func=service.postprolong&sok=ok&elid=" + str::Str(iid));
		
		item_params["partner_order_id"] = response.GetNode("//PartnerOrderID").Str();
		item_params[SERVICE_ORDER_ID] = response.GetNode("//CustomOrderID").Str();
		item_params["store_order_id"] = response.GetNode("//TheSSLStoreOrderID").Str();
		item_params["vender_order_id"] = response.GetNode("//VendorOrderID").Str();
		item_params["token_id"] = response.GetNode("//TokenID").Str();
		item_params["token_code"] = response.GetNode("//TokenCode").Str();
		
		SaveParam(iid, "partner_order_id", item_params["partner_order_id"]);
		SaveParam(iid, SERVICE_ORDER_ID, item_params[SERVICE_ORDER_ID]);
		SaveParam(iid, "store_order_id", item_params["store_order_id"]);
		SaveParam(iid, "vender_order_id", item_params["vender_order_id"]);
		SaveParam(iid, "token_id", item_params["token_id"]);
		SaveParam(iid, "token_code", item_params["token_code"]);
		
		try {
			SetServiceStatus(iid, ssl_util::isRequested);
			SyncItem(iid);
		} catch (mgr_err::Error& e) {
			Warning("can not sync ceertificate: %s", e.what());
		}
	}

	/**
	 * @brief Возобновить работу услуги
	 * @param [in] iid id услуги
	 */
	void Resume(const int iid)
	{
		sbin::ClientQuery("func=service.postresume&sok=ok&elid=" + str::Str(iid));
	}

	/**
	 * @brief Приостановить работу услуги
	 * @param [in] iid id услуги
	 */
	void Suspend(const int iid)
	{
		sbin::ClientQuery("func=service.postsuspend&sok=ok&elid=" + str::Str(iid));
	}

	/**
	 * @brief Отказаться от услуги
	 * @param [in] iid id услуги
	 */
	void Close(const int iid)
	{
		sbin::ClientQuery("func=service.postclose&sok=ok&elid=" + str::Str(iid));
	}

	/**
	 * @brief Синхронизировать состояние услуги и данных BILLmanager 5
	 * @param [in] iid id услуги
	 */
	void SyncItem(const int iid)
	{
		Init(iid);
		
		mgr_xml::Xml request;
		request.SetRoot("OrderRequest");
		SetAuth(request);
		
		// TheSSLStoreOrderID если CustomOrderID пусто
		if (!item_params["store_order_id"].empty()) {
			request.GetRoot().AppendChild("TheSSLStoreOrderID", item_params["store_order_id"]);
		} else {
			request.GetRoot().AppendChild("CustomOrderID", item_params[SERVICE_ORDER_ID]);
		}
		
		mgr_xml::Xml response = ApiRequest("order", "status", request.Str(true), POST);
		
		string major_status = response.GetNode("//OrderStatus/MajorStatus").Str();
		major_status = str::Lower(major_status);
		string minor_status = response.GetNode("//OrderStatus/MinorStatus").Str();
		minor_status = str::Lower(minor_status);
		Debug("major_status: %s, minor_status: %s", major_status.c_str(), minor_status.c_str());
		//Обработка дополнительных статусов. Проверка безопасности и прочее
		
		if (major_status == "pending" || minor_status == "pending_reissue") {
			SetServiceStatus(iid, ssl_util::isEnrolled);
		} else if (major_status == "cancelled") {
			SetServiceStatus(iid, ssl_util::isFailed);
		} else if (major_status == "active" && (minor_status != "pending_reissue")) {
			mgr_xml::Xml request;
			request.SetRoot("OrderRequest");
			SetAuth(request);
			if (!item_params["store_order_id"].empty()) {
				request.GetRoot().AppendChild("TheSSLStoreOrderID", item_params["store_order_id"]);
			} else {
				request.GetRoot().AppendChild("CustomOrderID", item_params[SERVICE_ORDER_ID]);
			}
			
			mgr_xml::Xml response = ApiRequest("order", "download", request.Str(true), POST);
			string end_date = response.GetNode("//CertificateEndDate").Str();
			string month = str::GetWord(end_date, "/");
			string day = str::GetWord(end_date, "/");
			string year = str::GetWord(end_date, " ");
			end_date = mgr_date::Date(year + "-" + month + "-" + day).operator string();
			
			Debug("end_date: %s", end_date.c_str());

			string file_name = item_params["CN"];
			file_name = str::Replace(file_name, "*", "STAR");
			file_name = str::Replace(file_name, ".", "_");
			file_name += ".crt";

			string crt = response.GetNode("//Certificates/Certificate[FileName='" + file_name + "']/FileContent").Str();
			if (crt.empty()) 
				crt = response.GetNode("//Certificates/Certificate[FileName='ServerCertificate.cer']/FileContent").Str();
			if (crt.empty()) 
				crt = response.GetNode("//Certificates/Certificate[FileName='" + item_params["vender_order_id"] + ".crt']/FileContent").Str();

			sbin::ClientQuery("func=certificate.save&elid=" + str::Str(iid) + "&crt=" + str::url::Encode(crt));

			SetServiceStatus(iid, ssl_util::isIssued);
			
			if (item_params[SERVICE_STATUS] != str::Str(ssl_util::isIssued)) {
				SetServiceExpireDate(iid, end_date);
				sbin::ClientQuery("func=certificate.open&sok=ok&elid=" + str::Str(iid));
			}
		}
	}

	/**
	 * @brief Переоткрыть услугу
	 * @param [in] iid id услуги
	 */
	void Reopen(const int iid)
	{
		Init(iid);
		
		mgr_xml::Xml request;
		request.SetRoot("ReissueOrderRequest");
		SetAuth(request);
		request.GetRoot().AppendChild("TheSSLStoreOrderID", item_params["store_order_id"]);
		request.GetRoot().AppendChild("CSR", item_params["csr"]);
		request.GetRoot().AppendChild("WebServerType", "Other");
		request.GetRoot().AppendChild("isWildCard", item_params["CN"][0] == '*' ? "true" : "false");
		request.GetRoot().AppendChild("ReissueEmail", item_params["approver_email"]);

		StringSet san;
		str::Split(item_params[CERTIFICATE_ALTNAME], san, " ");

		StringSet old_san;
		str::Split(item_params[CERTIFICATE_OLDALTNAME], old_san, " ");

		StringSet diff;
		std::set_intersection(san.begin(), san.end(), old_san.begin(), old_san.end(), std::inserter(diff, diff.begin()));
		
		if (!diff.empty()) { // Если получаем не нулевое пересечение старых и новых altname то добавляем соотвествующие поля в запрос
			mgr_xml::XmlNode dns_names;
			if (!san.empty())
				dns_names = request.GetRoot().AppendChild("DNSNames");

			auto del_san = request.GetRoot().AppendChild("DeleteSAN");
			auto add_san = request.GetRoot().AppendChild("AddSAN");

			ForEachI(san, s) {
				dns_names.AppendChild("string", *s);
				if (old_san.find(*s) == old_san.end())
					add_san.AppendChild("Pair").AppendChild("NewValue", *s);
			}

			ForEachI(old_san, s) {
				if (san.find(*s) == san.end())
					del_san.AppendChild("Pair").AppendChild("NewValue", *s);
			}
		} else { // Если пересечение нулевое значит удаляем старые и добавляем новые домены
			mgr_xml::XmlNode dns_names;
			if (!san.empty())
				dns_names = request.GetRoot().AppendChild("DNSNames");

			auto add_san = request.GetRoot().AppendChild("AddSAN");
			ForEachI(san, s) {
				dns_names.AppendChild("string", *s);
				add_san.AppendChild("Pair").AppendChild("NewValue", *s);
			}

			auto del_san = request.GetRoot().AppendChild("DeleteSAN");
			ForEachI(old_san, s) {
				del_san.AppendChild("Pair").AppendChild("NewValue", *s);
			}
		}

		mgr_xml::Xml response = ApiRequest("order", "reissue", request.Str(true), POST);
		
		SetServiceStatus(iid, ssl_util::isRequested);
	}

	/**
	 * @brief Получить список email-адресов для технического контакта сертификата
	 * @param [in] iid id услуги
	 */
	virtual mgr_xml::Xml ApproverList(const int mid, const string& domain, const string& intname) 
	{
		SetModule(mid);
		
		std::stringstream scsr; 
		scsr << std::cin;
		string csr = scsr.str();
		
		string tmp_domain = domain;
		string main_domain = str::RGetWord(tmp_domain, ".");
		main_domain = str::RGetWord(tmp_domain, ".") + "." + main_domain;
		
		mgr_xml::Xml request;
		request.SetRoot("NewOrderRequest");
		SetAuth(request);
		request.GetRoot().AppendChild("CSR", csr);
		request.GetRoot().AppendChild("ProductCode", intname);
		request.GetRoot().AppendChild("ServerCount", "1");
		request.GetRoot().AppendChild("AddInstallationSupport", "false");
		request.GetRoot().AppendChild("DomainName", domain);
		request.GetRoot().AppendChild("ReserveSANCount", "0");
		request.GetRoot().AppendChild("ValidityPeriod", "12");
		request.GetRoot().AppendChild("WebServerType", "Other");
		request.GetRoot().AppendChild("EmailLanguageCode", "EN");
		request.GetRoot().AppendChild("isRenewalOrder", "false");

		mgr_xml::Xml response = ApiRequest("order", "approverlist", request.Str(true), POST);

		StringSet approver_email;
		ForEachI(response.GetNodes("//ApproverEmailList/string"), r) {
			string email = r->Str();
			email = str::RGetWord(email);
			if (email == "none" || email.empty() || email.find(main_domain) == string::npos) continue;

			approver_email.insert(email);
		}

		mgr_xml::Xml approver;
		ForEachI(approver_email, email)
			approver.GetRoot().AppendChild("approver", *email);
		
		return approver;
	};

	/**
	 * @brief Настроить форму создания аккаунта TheSSLStore
	 * @param [in] module_xml XML с параметрами формы
	 */
	void TuneUserCreate(mgr_xml::Xml& module_xml)
	{
		module_xml.GetRoot().AppendChild("outerlink", "https://www.thesslstore.com?aid=52910611");
	}
};

#define RUN_MODULE(NAME) int ISP_MAIN(int argc, char *argv[]) { \
	sbin::Init(BINARY_NAME); \
	std::shared_ptr<processing::Module> module(new NAME()); \
	return module->Run(argc, argv); \
}

RUN_MODULE(TheSSLStore)
