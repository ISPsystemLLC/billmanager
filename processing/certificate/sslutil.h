#ifndef __SSLUTILS_H__
#define __SSLUTILS_H__

#include <mgr/mgrdb_struct.h>
#include <mgr/mgrlog.h>
#include "defines.h"
#include "common.h"

#define DEFAULT_KEY_LENGHT 2048

namespace ssl_util {
	enum CertificateStatus {
		isUnknown	= 0,	//Неизвестный - не используется в 5й версии
		isOrdered	= 1,	//Заказан (не оплачен) - не используется в 5й версии
		isPaied		= 2,	//Оплачен (не обработан) - не используется в 5й версии
		isRequested = 3,	//Запрос на сертификат отправлен
		isEnrolled	= 4,	//Сертификат ожидает выпуска
		isIssued	= 5,	//Сертификат выпущен
		isFailed	= 6		//Ошибка при оформлении сертификата
	};
	/**
	* @brief Возвращает шаблон сертификата
	*/
	struct Template {
		string name;
		bool is_wildcard;	// сертификат выдаётся на все поддомены *.mydomain.com
		bool is_www;		// сертификат выдаётся на домен domain.com и www.domain.com
		bool is_multidomain;// SAN сертификат

		bool is_idn;		// сертификат с поддержкой IDN
		bool is_orginfo;	// требуется указать информацию о организации

		bool is_codesign;	// Code Signing сертификат
		bool is_csraltname;	// добавляем subjectAltName в CSR заброс

		Template(mgr_xml::XmlNode tmpl_node);
		void AsXml(mgr_xml::Xml& xml);

		typedef std::map<string, std::list<Template> > TemplateMap;

		static TemplateMap& Get();

		static void Insert(const string& module, mgr_xml::XmlNode config);
		static void AsXml(const string& module, mgr_xml::Xml &xml);
	};

	/**
	 * @brief Возвращает коичество AltName-ов для заказываемого сертификата
	 * @param [in] db указатель на объект базы данных.
	 * @param [in] iid идентификатор услуги.
	 */
	int OrderedAltNamesCount(std::shared_ptr<mgr_db::Cache> db, int iid);
}

#endif