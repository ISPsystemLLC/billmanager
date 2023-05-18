#ifndef __MODULE_H__
#define __MODULE_H__

#include <mgr/mgrtest.h>
#include "defines.h"
#include "util.h"
#include "common.h"

namespace opts {

class Args;

class Arg {
public:
	typedef Arg * Ptr;
	std::string Name;
	char ShortName;
	bool Exists;
	std::string Opt;
	bool HasOpt;
	bool Required;
	bool RequireValue;
	Arg (const std::string &name, Args * parent, bool required=true,  bool requireValue=true);
	Arg (const std::string &name, char shortName, Args * parent, bool required=true, bool requireValue=true);
	Arg (char shortName, Args * parent, bool required=true, bool requireValue=true);
	inline operator std::string() const { return Opt; }
	inline std::string AsString() const { return Opt; }
	string OnUsage() const;
	 /*
	  * Позволяет задать необходимость наличия значения у аргумента, в зависимости от наличия
	  *другого аргумента с определенным значением.
	  */
	void Depends(Ptr depends, const string& value);
	void SetValidator(test::Valid validator);
	void SetPosition (int pos);
protected:
	std::vector<std::pair<Ptr, string> > m_depends;
	test::Valid m_validator;
	int m_position;

	friend class Args;
};

class Args {
private:
	std::vector <Arg::Ptr> m_Args;
	std::vector<std::string> m_Other;
	std::vector<std::string> m_Unrecognized;
public:
	Arg Help;
	Arg Version;
	Arg IspOpt;
	Args();
	void Register (Arg::Ptr arg);
	Arg::Ptr Get (const std::string &name);
	Arg::Ptr Get (char name);
	bool Parse (int argc, char **argv);
	template <class O>
	void GetOther (O & other)
	{
		std::copy (m_Other.begin (), m_Other.end (), std::back_inserter (other));
	}

	template <class O>
	void GetUnrecognized (O & other)
	{
		std::copy (m_Unrecognized.begin (), m_Unrecognized.end (), std::back_inserter (other));
	}
	virtual ~Args() {}
protected:
	virtual void OnUsage (const std::string &argv0) {}
	virtual void OnVersion (const std::string &argv0) {}
    virtual void OnUnrecognize (const std::vector<std::string> & unrecognized);

private:
	int paramType (const std::string &param);
	int parseOne (const std::string & argv0, const std::string *argv1);

};

class ModuleArgs : public opts::Args
{
private:
	string ArgAsString(opts::Arg& arg);
public:
	opts::Arg Command;
	opts::Arg SubCommand;
	opts::Arg Id;
	opts::Arg Item;
	opts::Arg Lang;
	opts::Arg Module;
	opts::Arg ItemType;
	opts::Arg IntName;
	opts::Arg Param;
	opts::Arg Value;
	opts::Arg RunningOperation;
	opts::Arg Level;//уровень выполнения клиента. lvAdmin, lvClient
	opts::Arg Addon;//id аддона

	ModuleArgs ();

	void OnUsage(const string &argv0);
	void OnVersion(const string &argv0);

	void OnUnrecognize (const std::vector<string> &unrecognized);

	string AsString();
};

class CertificateModuleArgs : public ModuleArgs
{
public:
	opts::Arg Domain;

	CertificateModuleArgs();
};

}

namespace processing {

/**
 * @brief Заполняет params парметрами модуля обработки с идентификатором module
 * @param [in] module идентификатор модуля обработки
 * @param [in] params StringMap для записи параметр обработчика
 */
void FillModuleParams(const int module, StringMap& params);

class ModuleError {
public:
	ModuleError(const int loglines = 100);
	void SetProcessingModule(const int module_id);
	void SetProcessingModuleByItem(const int iid);
	ModuleError& AddError(const mgr_err::Error &error, const bool global = false);
	ModuleError& AddError(const mgr_xml::Xml &errorxml);
	ModuleError& AddLastErrorParam(const string& name, const string& value);
	enum CustomMessageType {
		cmInfo	= 0,
		cmError	= 1
	};
	ModuleError& AddCustomMessage(const string& message, const CustomMessageType type = cmInfo);
	ModuleError& AddLastCustomMessageParam(const string& name, const string& value);
	ModuleError& AddLastCustomMessageMsgParam(const string& name, const string& value);

	mgr_xml::Xml AsXml();
	string AsString();
private:
	int m_loglines_count;
	mgr_xml::Xml m_xml;
	mgr_xml::XmlNode m_last_module;
	mgr_xml::XmlNode m_last_error;
	mgr_xml::XmlNode m_last_custommessage;
};

class Module {
public:
	Module(const string& name);

	virtual int Run(int argc, char *argv[]);
	virtual mgr_xml::Xml Features() = 0;
	virtual mgr_xml::Xml GetSuitableModule(mgr_xml::Xml item_xml);
	virtual void CheckConnection(mgr_xml::Xml module_xml);
	virtual void TuneConnection(mgr_xml::Xml &module_xml);
	virtual void TuneUserCreate(mgr_xml::Xml &module_xml);
	virtual void TuneServiceProfile(const std::string &param, const std::string &value, mgr_xml::Xml &module_xml);
	virtual void ValidateServiceProfile(const string& param, const std::string &value, mgr_xml::Xml& module_xml);
	virtual void Open(const int iid) = 0;
	virtual void Resume(const int iid) = 0;
	virtual void Suspend(const int iid) = 0;
	virtual void CancelProlong(const int iid) {}
	virtual void Close(const int iid) = 0;
	/**
	 * @brief SetParam Изменение ресурсов или параметров у услуги
	 * @param iid
	 */
	virtual void SetParam(const int iid) = 0;

	static mgr_db::QueryPtr ItemQuery(const int iid, const bool use_cache = false);
	virtual void SyncPriceList(const int module) {}
	virtual void SyncServer(const int module) {}
	virtual void SyncIpList(const int module) {}
	virtual void GetServerConfig(const int module) {}
	/**
	 * @brief SyncItem Получение информации об услуге из панели управления или от провайдера услуг
	 * @param iid
	 */
	virtual void SyncItem(const int iid) {}
	virtual void Prolong(const int iid) {}
	virtual void ProlongAddon(const int iid, const int aid) {}
	/**
	 * @brief Reopen Повторная обработка услуги
	 * @param iid
	 */
	virtual void Reopen(const int iid) {}
	virtual void GetStat(const int mid) {}

	/**
	 * @brief GetContactType полчить список контактов
	 * @param tld
	 */
	virtual mgr_xml::Xml GetContactType(const string& tld);

	/**
	 * @brief TransitionControlPanel - Переход во внешнюю панель
	 * @param iid
	 * @param panel_key
	 */
	virtual mgr_xml::Xml TransitionControlPanel(const int iid, const string& panel_key);

	/**
	 * @brief Import - получение списка услуг из панели управления или от провайдера услуг.
	 * По шагам:
	 * 1. Получить список услуг
	 * 2. Получить список профилей
	 * 3. Сохранить профили
	 * 4. Сохранить услуги
	 * 5. Сохранить привязку профиля к услуге
	 * 6. Сохранить привязку профиля к модулю обработки
	 * @param mid - код модуля обработки
	 * @param itemtype - внутреннее имя типа услуг
	 * @param search - критерий поиска услуг
	 */
	virtual void Import(const int mid, const string& itemtype, const string& search) {};

	virtual mgr_xml::Xml ImportPriceList(const int mid, const string& sub_command, const int id) {return mgr_xml::Xml();}

	virtual mgr_xml::Xml ApproverList(const int mid, const string& domain, const string& intname) {return mgr_xml::Xml();};
	/**
	 * @brief CheckParam проверяет параметр введенный пользователем. В случае ошибки нужно генерировать throw.
	 * @param item_xml
	 * @param item_id
	 * @param param_name
	 * @param value
	 */
	virtual void CheckParam(mgr_xml::Xml item_xml, const int item_id, const string& param_name, const string& value) {};
	/**
	 * @brief CheckAddon проверяет значение аддона, введенное пользователем. В случае ошибки нужно генерировать throw.
	 */
	virtual void CheckAddon(mgr_xml::Xml item_xml, const int item_id, const string& param_name, const string& value) {}


	/**
	 * @brief GenKey Генерация ключа для софта
	 * @param item_id
	 */
	virtual void GenKey(const int item_id) {throw mgr_err::Error("unsupported command");}

	/**
	 * @brief SetServiceStatus - выставит в биллинге статус услуги
	 * @param item_id - код услуги в биллинге
	 * @param status - числовое значение статуса. Отличается в зависимости от типа услуги
	 */
	virtual void SetServiceStatus(const int item_id, int status);
	virtual void SetServiceExpireDate(const int item_id, mgr_date::Date expiredate);

	void SetServiceProfileExternalId(const int pm_id, string service_profile_id, const string& type, const string& externalid, const string& password = "");

	/**
	 * @brief ProcessCommand Обработка команд не вошедших в класс Module
	 */
	virtual void ProcessCommand() {};

	static void SaveParam(const int iid, const string& name, const string& value);
	static void DropParam(const int iid, const string& name);
	void AddItemParam(StringMap &params, const int iid);

	virtual void OnCustomParamTableFormTune(mgr_xml::Xml& xml, StringMap& ses_params) {}
	virtual string OnCustomParamTableSet(const string& paramname, mgr_xml::Xml& xml, StringMap& ses_params) {return "";}
	virtual void OnCustomParamTableGet(const string& paramname, mgr_xml::Xml& xml, StringMap& ses_params) {}
	virtual void OnCustomParamList(const int module, mgr_xml::Xml& xml, StringMap& ses_params, mgr_db::QueryPtr query) {}
	void TuneCustomParam(const string& action, mgr_xml::Xml &module_xml);

	int GetModule();
	string Name();
	ModuleError& GetModuleError();

	virtual ~Module() {}
private:
	StringMap m_replace_map;
	StringVector m_restricted_setparam;
	int m_module_id;
	void RegisterModuleErrorProblem(const string& type, const mgr_err::Error& error, const string& params = "");
protected:
	StringMap m_module_data;
	const string m_name;
	virtual opts::ModuleArgs* MakeModuleArgs();
	std::shared_ptr<opts::ModuleArgs> m_args;
	ModuleError m_module_error;

	enum class SkipCommand {
		scSetParam	= 1,
		scOpen		= 2,
		scBoth		= 3
	};
	std::map<string, SkipCommand> m_skip_param;
	void AddSkipParam(const string& name, const SkipCommand command = SkipCommand::scBoth);
	bool IsParamSkipped(const string& name, const SkipCommand command);

	void SetModule(const int module);
	virtual void OnSetModule(const int module) {}

	virtual bool AllowChooseServer() {
		return true;
	}

	virtual void InternalAddItemParam(StringMap &params, const int iid) {}

	//utils
	void AddRenameParam(const string& from, const string& to);
	string RenameParam(const string& name);
	void AddItemAddon(StringMap &params, const int iid, const int pricelist);
	void AddTldParam(StringMap &params, const int iid);
//	virtual string onAddIp(const int ip_id) {return "";}
//	virtual void onDelIp(const int ip_id) {}
	/**
	 * @brief GetMaxTryCount - максимальное количество попыток операции, после достижения
	 * которого она будет переведена в ручную обработку
	 * @param operation - текущая операция (PROCESSING_OPEN и пр.)
	 */
	virtual int GetMaxTryCount(const string& operation) {
		return 10;
	}
	virtual string GetCreateTaskParams() {
		return "";
	}

	friend class ModuleConfig;
	void SetConfig(const int elid, mgr_xml::Xml& config);
	mgr_xml::Xml GetConfig(const int elid);
	/**
	 * @brief SetManualRerun Отключает автоматический перезапуск операции
	 * @param runningoperation
	 */
	void SetManualRerun(const int runningoperation);
	/**
	 * @brief CreateTask - создает задачу, переводит текущую операцию в ручную обработку
	 * @param iid - id услуги
	 * @param type - тип задачи
	 * @param params - доп. параметры для задачи
	 * @param uniq - если true - не создает задачу, если уже есть такая
	 */
	void CreateTask(const int iid, const string& type, const string& params = "", const bool uniq = false);
	StringMap ParamMeasure;
};

}

#endif