#include "module.h"
#include <sstream>
#include <iostream>
#include <stdexcept>
#include <mgr/mgrerr.h>
#include <mgr/mgrstr.h>
#include <mgr/mgrlog.h>
#include <mgr/mgrjob.h>

using namespace std;

MODULE ("module");

namespace opts {

static string getArgName (Arg::Ptr arg) {
	string result;
	if (arg->Name.empty ())
		result += arg->ShortName;
	else
		result = arg->Name;
	return result;
}
	
Arg::Arg (const string &name, Args *parent, bool required, bool requireValue)
	: Name			(name)
	, ShortName		(0)
	, Exists		(false)
	, HasOpt		(false)
	, Required		(required)
	, RequireValue	(requireValue)
	, m_validator	(nullptr)
	, m_position	(-1) {
	parent->Register (this);
	}

Arg::Arg (const string &name, char shortName, Args *parent, bool required, bool requireValue)
	: Name			(name)
	, ShortName		(shortName)
	, Exists		(false)
	, HasOpt		(false)
	, Required		(required)
	, RequireValue	(requireValue)
	, m_validator	(nullptr)
	, m_position	(-1)
{
    parent->Register (this);
}
Arg::Arg (char shortName, Args *parent, bool required, bool requireValue)
	: ShortName		(shortName)
	, Exists		(false)
	, HasOpt		(false)
	, Required		(required)
	, RequireValue	(requireValue)
	, m_validator	(nullptr)
	, m_position	(-1) {
	parent->Register (this);
}

string Arg::OnUsage() const {
	stringstream out;
	out << "\t";
	if (ShortName)
		out << "-" << ShortName;
	if (ShortName && !Name.empty())
		out << " | ";
	if (!Name.empty())
		out << "--" << Name;
	return out.str();
}

void Arg::Depends(Arg::Ptr depends, const string &value) {
	m_depends.push_back(std::make_pair(depends, value));
	RequireValue = true;
}

void Arg::SetValidator(test::Valid validator) {
	m_validator = validator;
}

void Arg::SetPosition(int pos) {
	m_position = pos;
}

int Args::paramType (const string &param) {
    if (param.empty ())
        return -1;
    if (param == "-" || param == "--") return 0;
    string::size_type pos = param.find_first_not_of ('-');
    if (pos > 2) pos = 2;
    return pos;
}

Args::Args()
    : Help ("help", 'h', this, false, false)
    , Version ("version", 'V', this, false, false)
	, IspOpt ('T', this, false, false) {}

void Args::Register (Arg::Ptr arg) {
	Debug ("Register %s (%c)", arg->Name.c_str (), arg->ShortName);
    for (vector <Arg::Ptr>::iterator i = m_Args.begin (); i != m_Args.end (); ++i) {
		if ((*i)->ShortName && (*i)->ShortName == arg->ShortName ) {
			cerr << "\tDublicate argument " << getArgName (*i) << endl;
			throw mgr_err::Error("dublicate").add_param ("name", getArgName (*i));

		}
		if (!(*i)->Name.empty() && (*i)->Name == arg->Name) {
			cerr << "\tDublicate argument " << getArgName (*i) << endl;
			throw mgr_err::Error("dublicate").add_param ("name", getArgName (*i));
        }
    }
    m_Args.push_back (arg);
}

Arg::Ptr Args::Get (const string &name) {
    for (vector <Arg::Ptr>::iterator i = m_Args.begin (); i != m_Args.end (); ++i) {
        if ((*i)->Name == name)
            return *i;
    }
	cerr << "\tArgument missed " << name << endl;
	throw mgr_err::Missed ("argument", name);
}

Arg::Ptr Args::Get (char name) {
    for (vector <Arg::Ptr>::iterator i = m_Args.begin (); i != m_Args.end (); ++i) {
        if ((*i)->ShortName == name)
            return *i;
    }
	cerr << "\tArgument missed " << name << endl;
	throw mgr_err::Missed ("argument", str::Str(name));
}

//Передаю пару...
// Возвращаем сколько нужно пропустить дополнительно
int Args::parseOne (const string & argv0, const string * argv1) {
    if (argv0.empty ())
        return 0;
    int pType = paramType (argv0);
    if (pType == 0) {
        m_Other.push_back (argv0);
        return 0;
    }
    int skip = 0;
    bool parsed = false;
    if (pType == 1) {
        // Short param
        for (vector <Arg::Ptr>::iterator i = m_Args.begin(); i != m_Args.end(); ++i)  {
            if (!(*i)->ShortName) continue;
            if ((*i)->Exists) continue;
            string::size_type spPos = argv0.find ((*i)->ShortName);
            bool last = spPos == argv0.length () - 1;
            if (spPos != string::npos) {
                (*i)->Exists = true;
                parsed = true;
            }
            if ((*i)->RequireValue) {
				if (last && argv1) {
					(*i)->Opt = *argv1;
                    (*i)->HasOpt = true;
                    skip = 1;
                } else {
                    (*i)->HasOpt = false;
                }
            }
        }
    } else if (pType == 2) {
        // long param
        for (vector <Arg::Ptr>::iterator i = m_Args.begin(); i != m_Args.end(); ++i) {
            if ((*i)->Name.empty()) continue;
            if (argv0 == "--" + (*i)->Name) {
                (*i)->Exists = true;
                parsed = true;
                if ((*i)->RequireValue) {
					if (argv1) {
						(*i)->Opt = *argv1;
                        (*i)->HasOpt = true;
                        skip = 1;
                    } else {
                        (*i)->HasOpt = false;
                    }
                }
            }
        }
    }
    if (!parsed) {
       m_Unrecognized.push_back (argv0);
    }
    return skip;
}

static
const char *eolColor = "\033[0m";

static
const char *Color[] = {
	"\033[34m",
	"\033[1;34m",
	"\033[1;31m",
	"\033[1;31m",
	"\033[1;35m",
	"\033[1;32m",
	"\033[1;36m",
	"\033[36m",
	"\033[1m",
	"\033[1;33m"
};

void Args::OnUnrecognize(const std::vector<string> &unrecognized) {
    ForEachI (unrecognized, opt) {
        Warning ("Unrecognized option: %s", opt->c_str());
        cerr << "unrecognized option: " << *opt << endl;
    }
}

bool Args::Parse(int argc, char **argv) {
    int currentArg = 1;
    while (currentArg <= argc - 1) {
        string argv0 = argv[currentArg];
        string argv1 = (currentArg < argc - 1) ? argv[currentArg + 1] : "";
		int skip = parseOne (argv0, (currentArg < argc - 1) ? &argv1 : nullptr);
        currentArg += 1 + skip;
    }
	if (IspOpt.Exists) {
		cout << "(c) ISPsystem.com";
		exit(0);
	}
	if (!m_Unrecognized.empty ()) {
		OnUnrecognize(m_Unrecognized);
		exit (1);
	}
	if (Help.Exists || m_Args.empty ()) {
		OnUsage(argv[0]);
		exit (0);
	}
	if (Version.Exists) {
		OnVersion (argv[0]);
		exit (0);
	}
    // check values
	bool missed = false;
    for (vector <Arg::Ptr>::iterator i = m_Args.begin(); i != m_Args.end(); ++i) {
        Arg::Ptr arg = *i;
		bool Required = arg->Required;
		bool RequireValue = arg->RequireValue;

		ForEachI (arg->m_depends, e) {
			if (e->first->Opt == e->second) {
				Required = true;
				RequireValue = true;
				break;
			}
		}
		if (!arg->Exists
				&& arg->m_position != -1
				&& m_Other.size() > (vector <Arg::Ptr>::size_type) arg->m_position )
		{
			arg->Exists = true;
			arg->HasOpt = true;
			arg->Opt = m_Other[arg->m_position];

		}
		if (Required & !arg->Exists) {
			cerr  << "\tMissed argument " << Color[3] << getArgName (arg) << eolColor << endl;
			missed = true;
        }
		if (arg->Exists && RequireValue && !arg->HasOpt) {
			cerr << "\tArgument " << Color[3] << getArgName (arg) << eolColor<< " require value" << endl;
			missed = true;
        }
		if (arg->m_validator && arg->Exists && !arg->m_validator(arg->Opt)) {
			cerr << "\tArgument " << Color[3] << getArgName (arg) << eolColor<< " has invalid value" << endl;
			missed = true;
		}

    }
	if (missed) {
		OnUsage (argv[0]);
		exit (1);
	}
	return !missed;
}

ModuleArgs::ModuleArgs()

    : Command				("command",		'c', this)
    , SubCommand			("subcommand",		 this, false, false)
    , Id					("id",				 this, false, false)
    , Item					("item",		'i', this, false, true)
    , Lang					("lang",		'l', this, false, true)
    , Module				("module",		'm', this, false, true)
    , ItemType				("itemtype",	't', this, false, false)
    , IntName				("intname",		this, false, false)
    , Param					("param",		this, false, true)
    , Value					("value",		this, false, true)
	, RunningOperation		("runningoperation",	this, false, true)
	, Level					("level", this, false, true)
	, Addon					("addon",		'a', this, false, true)
{
	Item.Depends(&Command, PROCESSING_OPEN);
	Item.Depends(&Command, PROCESSING_RESUME);
	Item.Depends(&Command, PROCESSING_SUSPEND);
	Item.Depends(&Command, PROCESSING_CLOSE);
	Item.Depends(&Command, PROCESSING_DOMAIN_UPDATE_NS);
	Item.Depends(&Command, PROCESSING_CHECK_PARAM);
	Item.Depends(&Command, PROCESSING_GEN_KEY);
	Item.Depends(&Command, PROCESSING_DOMAIN_TRANSFER);
	Item.Depends(&Command, PROCESSING_PROLONG);
	Item.Depends(&Command, PROCESSING_SETPARAM);
	Item.SetValidator(&test::Numeric);
	Level.SetValidator(&test::Numeric);

	//TODO: Id.Depends
	Id.Depends(&SubCommand, "pricelist");
	SubCommand.Depends(&Command, PROCESSING_PRICELIST_IMPORT);

	Module.Depends(&Command, PROCESSING_SYNC_PRICELIST);
	Module.Depends(&Command, PROCESSING_SYNC_SERVER);
	Module.Depends(&Command, PROCESSING_SYNC_IPLIST);
	Module.Depends(&Command, PROCESSING_GET_SERVER_CONFIG);
	Module.Depends(&Command, PROCESSING_SERVICE_IMPORT);
	Module.Depends(&Command, PROCESSING_CERTIFICATE_APPROVER);
	Module.Depends(&Command, PROCESSING_PRICELIST_IMPORT);
	Module.SetValidator(&test::Numeric);

	RunningOperation.SetValidator(&test::Numeric);
	ItemType.Depends(&Command, PROCESSING_SERVICE_IMPORT);

	IntName.Depends(&Command, PROCESSING_CERTIFICATE_APPROVER);
	Param.Depends(&Command, PROCESSING_CHECK_PARAM);
	Param.Depends(&Command, PROCESSING_SERVICE_PROFILE_FORM_TUNE);
}

void ModuleArgs::OnUsage(const string &argv0)
{
	std::cout << std::endl << "processing module" << std::endl;
	std::cout << std::endl << "Usage: binaryname --command <command>" << std::endl;
	std::cout << std::endl;
}

void ModuleArgs::OnVersion(const string &argv0) {
	std::cout << "1.0" << std::endl;
}

void ModuleArgs::OnUnrecognize(const std::vector<string> &unrecognized) {
	ForEachI (unrecognized, opt) {
		Warning ("Unrecognized option: %s", opt->c_str());
		std::cerr << "unrecognized option: " << *opt << std::endl;
	}
}

std::string ModuleArgs::ArgAsString(opts::Arg& arg) {
	return arg.Exists ? string("--" + arg.Name + " " + (string)arg) : "";
}

std::string ModuleArgs::AsString() {
	string result;
	str::inpl::Append(result, ArgAsString(Command), " ");
	str::inpl::Append(result, ArgAsString(SubCommand), " ");
	str::inpl::Append(result, ArgAsString(Id), " ");
	str::inpl::Append(result, ArgAsString(Item), " ");
	str::inpl::Append(result, ArgAsString(Lang), " ");
	str::inpl::Append(result, ArgAsString(Module), " ");
	str::inpl::Append(result, ArgAsString(ItemType), " ");
	str::inpl::Append(result, ArgAsString(IntName), " ");
	str::inpl::Append(result, ArgAsString(Param), " ");
	str::inpl::Append(result, ArgAsString(Value), " ");
	str::inpl::Append(result, ArgAsString(RunningOperation), " ");
	str::inpl::Append(result, ArgAsString(Level), " ");
	str::inpl::Append(result, ArgAsString(Addon), " ");

	return result;
}

CertificateModuleArgs::CertificateModuleArgs()
	: ModuleArgs()
	, Domain				("domain",		this, false, false) {
	Domain.Depends(&Command, PROCESSING_CERTIFICATE_APPROVER);
}

}

namespace processing {

void FillModuleParams(const int module, StringMap &params) {
	params.clear();
	ForEachQuery(sbin::DB(), "select intname, value "
	                         "from processingparam where processingmodule=" + str::Str(module), entry)
	        params[entry->AsString("intname")] = entry->AsString("value");
	ForEachQuery(sbin::DB(), "select intname, value "
	                         "from processingcryptedparam where processingmodule=" + str::Str(module), entry)
	        params[entry->AsString("intname")] = util::DecryptValue(sbin::GetMgrConfParam(ConfCryptKey, DefaultCryptKey), entry->AsString("value"));
}

ModuleError::ModuleError(const int loglines) : m_loglines_count(loglines) {}

void ModuleError::SetProcessingModule(const int module_id) {
	const string name = sbin::DB()->Query("SELECT name FROM processingmodule WHERE id = " + str::Str(module_id))->Str();
	m_last_module = m_xml.GetRoot().AppendChild("processingmodule");
	m_last_module
	        .SetProp("date", mgr_date::DateTime())
	        .SetProp("id", str::Str(module_id))
	        .SetProp("name", name);
}

void ModuleError::SetProcessingModuleByItem(const int iid) {
	const int module_id = sbin::DB()->Query("SELECT processingmodule FROM item WHERE id = " + str::Str(iid))->Int();
	SetProcessingModule(module_id);
}

ModuleError& ModuleError::AddError(const mgr_err::Error &error, const bool global) {
	string bt;
	for (error.backtrace().First(); error.backtrace().Next();) {
		str::inpl::Append(bt, error.backtrace().AsString(), "\n");
	}
	if (global)
		m_last_error = m_xml.GetRoot().AppendChild("error");
	else
		m_last_error = m_last_module ? m_last_module.AppendChild("error") : m_xml.GetRoot().AppendChild("error");

	m_last_error
	        .SetProp("date", mgr_date::DateTime())
	        .SetProp("type", error.type())
	        .SetProp("object", error.object())
	        .SetProp("value", error.value());
	auto params = error.xml().GetNodes("/doc/error/param");
	ForEachI(params, p) {
		m_last_error.AppendChild(*p);
	}
	m_last_error.AppendChild("backtrace").AppendCData(bt);

	error.backtrace().First();
	StringVector loglines;
	str::Split(mgr_log::GetThreadLog(), "\n", loglines);
	string log;
	if (!loglines.empty()) {
		auto bt_start = 0;
		bool fnd = false;
		ForEachI(loglines, line) {
			if (line->find(error.backtrace().AsString()) != string::npos) {
				fnd = true;
				break;
			}
			++bt_start;
		}
		if (!fnd) bt_start = loglines.size() - 1;
		bt_start -= m_loglines_count;
		if (bt_start < 0) bt_start = 0;
		for (size_t i = bt_start; i < loglines.size(); ++i) {
			log += loglines.at(i) + "\n";
		}
	}
	m_last_error.AppendChild("log").AppendCData(log);//mgr_log::GetThreadLog());
	return *this;
}

ModuleError &ModuleError::AddError(const mgr_xml::Xml &errorxml) {
	auto err = errorxml.GetNode("/doc/error");
	if (err)
		m_last_error = m_last_module ? m_last_module.AppendChild(err) : m_xml.GetRoot().AppendChild(err);
	return *this;
}

ModuleError& ModuleError::AddLastErrorParam(const std::string &name, const std::string &value) {
	if (m_last_error)
		m_last_error.SetProp(name.c_str(), value);
	return *this;
}

ModuleError &ModuleError::AddCustomMessage(const std::string &message, const CustomMessageType type) {
	m_last_custommessage = m_last_module ?
	            m_last_module.AppendChild("custommessage", message)
	          : m_xml.GetRoot().AppendChild("custommessage", message);
	m_last_custommessage.SetProp("date", mgr_date::DateTime());
	if (type == cmInfo)
		m_last_custommessage.SetProp("type", "info");
	else if (type == cmError)
		m_last_custommessage.SetProp("type", "error");
	return *this;
}

ModuleError &ModuleError::AddLastCustomMessageParam(const std::string &name, const std::string &value) {
	if (m_last_custommessage)
		m_last_custommessage.SetProp(name.c_str(), value);
	return *this;
}

ModuleError &ModuleError::AddLastCustomMessageMsgParam(const std::string &name, const std::string &value) {
	return AddLastCustomMessageParam("msg_" + name, value);
}

mgr_xml::Xml ModuleError::AsXml() {
	return m_xml;
}

std::string ModuleError::AsString() {
	return m_xml.Str();
}

Module::Module(const string& name): m_module_id (0), m_name (name) {}

int Module::Run(int argc, char *argv[]) {
	STrace();
	try {
		m_args.reset(MakeModuleArgs());
		m_args->Parse(argc, argv);

		Debug("run with: %s", m_args->AsString().c_str());

		if (m_args->RunningOperation.Exists) {
			mgr_log::StartThreadLog();
			if (m_args->Module.Exists)
				m_module_error.SetProcessingModule(str::Int(m_args->Module.AsString()));
			else if (m_args->Item.Exists)
				m_module_error.SetProcessingModuleByItem(str::Int(m_args->Item.AsString()));
		}

		if (m_args->Command.AsString() == PROCESSING_FEATURES)
		{
			std::cout << Features().Str(true);
		}
		else if (m_args->Command.AsString() == PROCESSING_OPEN)
		{
			if (util::DoNothing()) return 0;
			bool opened = false;
			const int iid = str::Int(m_args->Item);
			while (!opened) {
				try {
					try {
						Open(iid);
						opened = true;
					} catch (const mgr_err::Error& e) {
						m_module_error.AddError(e);
						throw;
					}
				} catch (const mgr_err::Error& e) {
					if (!AllowChooseServer())
						throw;
					if (e.type() == "client" || e.type() == "auth")
						RegisterModuleErrorProblem(PROBLEM_PROCESSINGMODULE_CONNECT, e);

					mgr_job::Rollback();
					sbin::ClientQuery("func=service.getnextmodule&elid=" + str::Str(iid));
					sbin::DB()->Commit();
					if (m_args->RunningOperation.Exists)
						m_module_error.SetProcessingModuleByItem(iid);

					const string iidname = sbin::DB()->Query("SELECT name FROM item WHERE id=" + str::Str(iid))->Str();
					RegisterModuleErrorProblem(PROBLEM_PROCESSINGMODULE_GETNEXTMODULE, e,
					                           "item_name=" + str::url::Encode(iidname) +
					                           "&iid=" + str::Str(iid));
				}
			}
		}
		else if (m_args->Command.AsString() == PROCESSING_RESUME)
		{
			if (util::DoNothing()) return 0;
			Resume(str::Int(m_args->Item));
		}
		else if (m_args->Command.AsString() == PROCESSING_SUSPEND)
		{
			if (util::DoNothing()) return 0;
			Suspend(str::Int(m_args->Item));
		}
		else if (m_args->Command.AsString() == PROCESSING_CANCEL_PROLONG)
		{
			if (util::DoNothing()) return 0;
			CancelProlong(str::Int(m_args->Item));
		}
		else if (m_args->Command.AsString() == PROCESSING_CLOSE)
		{
			if (util::DoNothing()) return 0;
			Close(str::Int(m_args->Item));
		}
		else if (m_args->Command.AsString() == PROCESSING_SETPARAM)
		{
			try {
				SetParam(str::Int(m_args->Item));
			} catch (...) {
				if (sbin::DB()->Query("SELECT lastpricelist FROM item WHERE id =" + str::Str(str::Int(m_args->Item)))->Int() > 0)
					sbin::ClientQuery("sok=ok&func=service.changepricelist.rollback&elid=" + str::url::Encode(m_args->Item));
				throw;
			}
		}
		else if (m_args->Command.AsString() == PROCESSING_GET_SUITABLE_MODULE)
		{

			mgr_xml::Xml item_xml;
			try {
				item_xml.Load(std::cin);
			} catch (mgr_err::Error& e){
				throw mgr_err::Error("failed to parse input xml");
			}
			Debug("item xml: %s", item_xml.Str(true).c_str());
			std::cout << GetSuitableModule(item_xml).Str(true);
		}
		else if (m_args->Command.AsString() == PROCESSING_CHECK_CONNECTION)
		{

			mgr_xml::Xml module_xml;
			try {
				module_xml.Load(std::cin);
			} catch (mgr_err::Error& e) {
				throw mgr_err::Error("failed to parse input xml");
			}
			Debug("module xml: %s", module_xml.Str(true).c_str());
			CheckConnection(module_xml);
			std::cout << mgr_xml::Xml().Str(true);
		}
		else if (m_args->Command.AsString() == PROCESSING_CONNECTION_FORM_TUNE)
		{

			mgr_xml::Xml form_xml;
			try {
				form_xml.Load(std::cin);
				TuneConnection(form_xml);
				std::cout << form_xml.Str();
			} catch (mgr_err::Error& e){
				throw mgr_err::Error("failed to parse input xml");
			}
		}
		else if (m_args->Command.AsString() == PROCESSING_TUNING_PARAM)
		{
			mgr_xml::Xml form_xml;
			try {
				form_xml.Load(std::cin);
			} catch (mgr_err::Error& e){
				throw mgr_err::Error("failed to parse input xml");
			}
			TuneCustomParam(m_args->SubCommand, form_xml);
			Debug("form_xml = '%s'", form_xml.Str().c_str());
			std::cout << form_xml.Str();
		}
		else if (m_args->Command.AsString() == PROCESSING_USERCREATE)
		{
			mgr_xml::Xml form_xml;
			try {
				form_xml.Load(std::cin);
				TuneUserCreate(form_xml);
				std::cout << form_xml.Str();
			} catch (mgr_err::Error& e){
				throw mgr_err::Error("failed to parse input xml");
			}
		}
		else if (m_args->Command.AsString() == PROCESSING_SERVICE_PROFILE_FORM_TUNE)
		{
			mgr_xml::Xml form_xml;
			try {
				form_xml.Load(std::cin);
				TuneServiceProfile(m_args->Param.AsString(), m_args->Value.AsString(), form_xml);
				std::cout << form_xml.Str();
			} catch (mgr_err::Error& e){
				throw mgr_err::Error("failed to parse input xml");
			}
		}
		else if (m_args->Command.AsString() == PROCESSING_SERVICE_PROFILE_VALIDATE)
		{
			mgr_xml::Xml param_xml;
			try {
				param_xml.Load(std::cin);
			} catch (mgr_err::Error& e) {
				throw mgr_err::Error("failed to parse input xml");
			}

			ValidateServiceProfile(m_args->Param.AsString(), m_args->Value.AsString(), param_xml);
			std::cout << param_xml.Str();
		}
		else if (m_args->Command.AsString() == PROCESSING_SYNC_PRICELIST)
		{
			SyncPriceList(str::Int(m_args->Module));
			GetServerConfig(str::Int(m_args->Module));
		}
		else if (m_args->Command.AsString() == PROCESSING_GET_SERVER_CONFIG)
		{
			GetServerConfig(str::Int(m_args->Module));
		}
		else if (m_args->Command.AsString() == PROCESSING_SYNC_SERVER)
		{
			SyncServer(str::Int(m_args->Module));
		}
		else if (m_args->Command.AsString() == PROCESSING_SYNC_IPLIST)
		{
			SyncIpList(str::Int(m_args->Module));
		}
		else if (m_args->Command.AsString() == PROCESSING_SYNC_ITEM)
		{
			if (util::DoNothing()) return 0;
			SyncItem(str::Int(m_args->Item));
		}
		else if (m_args->Command.AsString() == PROCESSING_PROLONG)
		{
			if (util::DoNothing()) return 0;
			Prolong(str::Int(m_args->Item));
		}
		else if (m_args->Command.AsString() == PROCESSING_PROLONG_ADDON)
		{
			if (util::DoNothing()) return 0;
			ProlongAddon(str::Int(m_args->Item), str::Int(m_args->Addon));
		}
		else if (m_args->Command.AsString() == PROCESSING_REOPEN)
		{
			if (util::DoNothing()) return 0;
			Reopen(str::Int(m_args->Item));
		}
		else if (m_args->Command.AsString() == PROCESSING_STAT)
		{
			if (util::DoNothing()) return 0;
			GetStat(str::Int(m_args->Module));
		}
		else if (m_args->Command.AsString() == PROCESSING_PRICELIST_IMPORT)
		{
			STrace();
			Debug("id='%s'", m_args->Id.AsString().c_str());
			std::cout << ImportPriceList(str::Int(m_args->Module), m_args->SubCommand, str::Int(m_args->Id)).Str(true);
		}
		else if (m_args->Command.AsString() == PROCESSING_CHECK_PARAM || m_args->Command.AsString() == PROCESSING_CHECK_ADDON)
		{
			mgr_xml::Xml item_xml;
			try {
				item_xml.Load(std::cin);
			} catch (mgr_err::Error& e){
				throw mgr_err::Error("failed to parse input xml");
			}
			Debug("item xml: %s", item_xml.Str(true).c_str());
			if (m_args->Command.AsString() == PROCESSING_CHECK_ADDON)
				CheckAddon(item_xml, str::Int(m_args->Item), m_args->Param, m_args->Value);
			else
				CheckParam(item_xml, str::Int(m_args->Item), m_args->Param, m_args->Value);
			mgr_xml::Xml out;
			out.GetRoot().AppendChild("ok");
			std::cout << out.Str(true);
		}
		else if (m_args->Command.AsString() == PROCESSING_GEN_KEY)
		{
			GenKey(str::Int(m_args->Item));
			mgr_xml::Xml out;
			out.GetRoot().AppendChild("ok");
			std::cout << out.Str(true);
		} else
		{
			ProcessCommand();
		}

		mgr_job::Commit();
	} catch (mgr_err::Error& e) {
		if (m_args->RunningOperation.Exists) {
			m_module_error.AddError(e, true);
			sbin::ClientQuery("func=runningoperation.edit&sok=ok&elid=" + m_args->RunningOperation.AsString() +
			                  "&errorxml=" + str::url::Encode(m_module_error.AsString()));
			if (m_args->Item.Exists) {
				//create task
				const string sql = "SELECT trycount FROM runningoperation WHERE id=" + m_args->RunningOperation.AsString();
				const string sql_exists = "SELECT COUNT(*) FROM task WHERE runningoperation=" + sbin::DB()->EscapeValue(m_args->RunningOperation.AsString());
				if (sbin::DB()->Query(sql)->Int() >= GetMaxTryCount(m_args->Command.AsString()) && sbin::DB()->Query(sql_exists)->Int() == 0) {
					SetManualRerun(str::Int(m_args->RunningOperation.AsString()));
					auto rs = sbin::ClientQuery("func=task.gettype&operation=" + str::url::Encode(m_args->Command.AsString()));
					string task_type = rs.xml.GetNode("/doc/task_type").Str();
					if (!task_type.empty()) {
						string cmd = "func=task.edit&item=" + str::url::Encode(m_args->Item) +
									 "&sok=ok&runningoperation=" + str::url::Encode(m_args->RunningOperation.AsString()) +
									 "&type=" + task_type +
									 "&params=" + str::url::Encode(GetCreateTaskParams());
						sbin::ClientQuerySafe(cmd);
					}
				}
			}
		}

		if (e.type() == "client" || e.type() == "auth")
			RegisterModuleErrorProblem(PROBLEM_PROCESSINGMODULE_CONNECT, e);

		Warning("%s", e.what());
		mgr_job::Rollback();
		std::cout << e.xml().Str(true) << std::endl;
		return EXIT_FAILURE;
	}

	return EXIT_SUCCESS;
}

mgr_xml::Xml Module::GetSuitableModule(mgr_xml::Xml item_xml) {
	const string pricelist = item_xml.GetNode("/doc/item/pricelist").Str();
	const string skip_modules = item_xml.GetNode("/doc/skip_modules").Str();
	mgr_xml::Xml xml;
	auto modules = xml.GetRoot().AppendChild("modules");

	string ipmgr_cond;
	if (!skip_modules.empty()) {
		string tmp = skip_modules;
		const int last_id = str::Int(str::RGetWord(tmp, ','));
		if (last_id) {
			const int ipmgr = sbin::DB()->Query("SELECT ipmgr FROM processingmodule WHERE id=" + str::Str(last_id))->Int();
			if (ipmgr &&
				sbin::DB()->Query("SELECT COUNT(*) FROM processingmodule WHERE id NOT IN (" + skip_modules + ") AND ipmgr=" + str::Str(ipmgr))->Int())
			{
				ipmgr_cond = " AND pm.ipmgr=" + str::Str(ipmgr);
			}
		}
	}

	ForEachQuery(sbin::DB(), "SELECT pm.id, pm.module "
				 "FROM processingmodule2pricelist pm2p "
				 "JOIN processingmodule pm ON pm.id=pm2p.processingmodule "
				 "WHERE pm2p.pricelist=" + sbin::DB()->EscapeValue(pricelist) + " " +
				 (skip_modules.empty() ? "" : ipmgr_cond + " AND pm.id NOT IN (" + skip_modules + ")") + " "
				 "AND pm.module=" + sbin::DB()->EscapeValue(m_name) + " "
				 "AND pm.active='on' "
				 "ORDER BY pm.orderpriority, pm.ipmgr, pm.id"
				 , entry)
	{
		modules.AppendChild("module").SetProp("id", entry->AsString("id"));
	}

	return xml;
}

void Module::CheckConnection(mgr_xml::Xml module_xml) {}

void Module::TuneConnection(mgr_xml::Xml& module_xml) {}

void Module::TuneUserCreate(mgr_xml::Xml& module_xml) {}

void Module::TuneServiceProfile(const string& param, const string& value, mgr_xml::Xml& module_xml) {}

void Module::ValidateServiceProfile(const string& param, const string& value, mgr_xml::Xml& module_xml) {}

mgr_xml::Xml Module::TransitionControlPanel(const int iid, const string& panel_key) {
	throw mgr_err::Error("not_supported");
}

void Module::SetServiceStatus(const int item_id, int status) {
	sbin::ClientQuery("func=service.setstatus&elid=" + str::Str(item_id) + "&" SERVICE_STATUS "=" + str::Str(status));
}

void Module::SetModule(const int module) {
	const string module_name = sbin::DB()->Query("SELECT module FROM processingmodule WHERE id = " + str::Str(module))->Str();
	if (!module_name.empty() && module_name != m_name)
		throw mgr_err::Error("unsupported_module", module_name, str::Str(module));
	m_module_id = module;
	m_module_data.clear();
	FillModuleParams(module, m_module_data);
	OnSetModule(module);
}

int Module::GetModule() {
	if (m_module_id == 0)
		throw mgr_err::Missed("module");
	return m_module_id;
}

void Module::SetServiceExpireDate(const int item_id, mgr_date::Date expiredate) {
	sbin::ClientQuery("func=service.setexpiredate&elid=" + str::Str(item_id) + "&expiredate=" + string(expiredate));
}

void Module::SetServiceProfileExternalId(const int pm_id, std::string service_profile_id, const std::string& type, const std::string& externalid, const std::string& password) {
	sbin::ClientQuery("func=service_profile2processingmodule.edit"
					  "&sok=ok"
					  "&service_profile=" + str::url::Encode(service_profile_id) +
					  "&processingmodule=" + str::url::Encode(str::Str(pm_id)) +
					  "&type=" + str::url::Encode(type) +
					  "&externalid=" + str::url::Encode(externalid) +
					  "&externalpassword=" + str::url::Encode(password));
}

void Module::SaveParam(const int iid, const std::string &name, const std::string &value) {
	sbin::ClientQuerySafe("func=service.saveparam&sok=ok"
						  "&elid=" + str::Str(iid) +
						  "&name=" + str::url::Encode(name) +
						  "&value="+ str::url::Encode(value));
}

void Module::DropParam(const int iid, const std::string &name) {
	sbin::ClientQuerySafe("func=service.saveparam&sok=ok"
						  "&elid=" + str::Str(iid) +
						  "&name=" + str::url::Encode(name));
}

mgr_db::QueryPtr Module::ItemQuery(const int iid, const bool use_cache) {
	STrace();
	static mgr_db::QueryPtr item_query;
	static bool initialized = false;

	if (!initialized || !use_cache) {
		item_query = sbin::DB()->Query("select it.intname, pm.module, i.id, i.remoteid, i.processingmodule, "
						"p.intname as pricelist_intname, i.pricelist, i.period, i.status, i.expiredate, i.opendate "
						"from item i "
						"left join pricelist p on p.id=i.pricelist "
						"left join itemtype it on it.id=p.itemtype "
						"left join processingmodule pm on pm.id=i.processingmodule "
						"where i.id=" + str::Str(iid));
		initialized = true;
	}
	if (item_query->Eof())
		throw mgr_err::Missed("item", str::Str(iid));
	return item_query;
}



mgr_xml::Xml Module::GetContactType(const string &tld) {
	return mgr_xml::Xml();
}

opts::ModuleArgs *Module::MakeModuleArgs() {
	return new opts::ModuleArgs();
}

void Module::AddSkipParam(const std::string &name, const Module::SkipCommand command) {
	if (!IsParamSkipped(name, command))
		m_skip_param[name] = command;
}

bool Module::IsParamSkipped(const std::string &name, const Module::SkipCommand command) {
	auto it = m_skip_param.find(name);
	return it != m_skip_param.end() && (it->second == SkipCommand::scBoth || it->second == command);
}

void Module::AddRenameParam(const string &from, const string &to) {
	m_replace_map[from] = to;
}

string Module::RenameParam(const string &name) {
	auto e = m_replace_map.find(name);
	if (e != m_replace_map.end())
		return e->second;
	return name;
}

void Module::AddItemAddon(StringMap &params, const int iid, const int pricelist) {
	ForEachQuery(sbin::DB(), "select distinct t.intname, if(p.addontype = " + str::Str(table::atEnum) + ", ifnull(ie.intname, pe.intname), "
				 "if(p.addontype = " + str::Str(table::atBoolean) + ", ifnull(i.boolvalue, p.addonbool), "
				 "if(p.billtype = " + str::Str(table::btStat) + ", if (i.addonlimit is null, if(p.addonmax is null, p.addonlimit, p.addonmax), i.addonlimit), "
				 "if(i.intvalue is null, if(i.addonlimit is null, p.addonlimit, i.addonlimit), if(i.addonlimit is null, p.addonlimit+i.intvalue, i.addonlimit+i.intvalue))))) "
				 "as value, if(p.addontype = " + str::Str(table::atInteger) + ", m.intname, '') as measure, "
				 "ifnull(i.enumerationitem, p.enumerationitem) as enumerationitem "
				 "FROM pricelist p left join itemtype t on p.itemtype = t.id "
				 "LEFT JOIN item i on i.pricelist = p.id and i.parent =  " + str::Str(iid) + " "
				 "LEFT JOIN enumerationitem ie on i.enumerationitem = ie.id "
				 "LEFT JOIN enumerationitem pe on p.enumerationitem=pe.id "
				 "LEFT JOIN measure m on m.id=p.measure "
				 "WHERE p.parent=" + str::Str(pricelist) + " "
				 "AND (p.active = 'on' OR i.id IS NOT NULL) "
				 "AND p.billtype!=" + str::Str(table::btCompound) + " "
				 "AND p.billtype!=" + str::Str(table::btManual) + " "
				 "AND (p.compound IS NULL OR i.id IS NOT NULL)"
				 , entry)
	{
		string value = entry->AsString("value");
		string intname = entry->AsString("intname");
		if (!entry->AsString("measure").empty() && !ParamMeasure[intname].empty()) {
			value = str::Str(str::Int64(value) * util::MeasureRelation(entry->AsString("measure"), ParamMeasure[intname], sbin::DB()->GetConnection()));
		}

		string paramname = RenameParam(intname);
		if (params.find(paramname) != params.end()) {
			Warning("replace param %s from %s to %s", paramname.c_str(), params[paramname].c_str(), value.c_str());
		}

		params[paramname] = value;
	}

	ForEachQuery(sbin::DB(), "SELECT * FROM pricelistparam WHERE pricelist=" + str::Str(pricelist), entry) {
		params[RenameParam(entry->AsString("intname"))] = entry->AsString("value");
	}
}

void Module::AddItemParam(StringMap &params, const int iid) {
	ForEachQuery(sbin::DB(), "select intname, value from itemparam where item=" + str::Str(iid), entry)
	{
		params[RenameParam(entry->AsString("intname"))] = entry->AsString("value");
	}

	InternalAddItemParam(params, iid);
}

void Module::TuneCustomParam(const std::string &action, mgr_xml::Xml &module_xml) {
	STrace();
	Debug("action='%s'", action.c_str());
	StringMap params;
	ForEachI(module_xml.GetNodes("/doc/session_params/*"), p) {
		params[p->GetProp("name")] = p->GetProp("value");
	}
	if (action == "TableFormTune")
		OnCustomParamTableFormTune(module_xml, params);
	else if (action == "List") {
		const int processingmodule = str::Int(params["elid"]);
		auto query = sbin::DB()->Query("SELECT * FROM processingparam WHERE processingmodule=" + str::Str(processingmodule));
		OnCustomParamList(processingmodule, module_xml, params, query);
		auto feature_xml = Features();
		ForEachRecord(query) {
			if (module_xml.GetNode("/doc/elem[id='" + query->AsString("id") + "']") || !feature_xml.GetNode("//customparam[@name='" + query->AsString("intname") + "']"))
				continue;
			auto elemnode = module_xml.GetRoot().AppendChild("elem");
			elemnode.AppendChild("id", query->AsString("id"));
			elemnode.AppendChild("param", query->AsString("intname"));
			elemnode.AppendChild("value", query->AsString("value"));
		}
	} else if (action == "TableGet")
		OnCustomParamTableGet(params["param"], module_xml, params);
	else if (action == "TableSet") {
		params["value"] = OnCustomParamTableSet(params["param"], module_xml, params);
	}

	module_xml.RemoveNodes("/doc/session_params/*");
	auto session_params = module_xml.GetRoot().AppendChild("session_params");
	ForEachI(params, p) {
		session_params.AppendChild("param").SetProp("name", p->first).SetProp("value", p->second);
	}
}

std::string Module::Name() {
	return m_name;
}

ModuleError &Module::GetModuleError() {
	return m_module_error;
}

void Module::RegisterModuleErrorProblem(const string& type, const mgr_err::Error& error, const string& params) {
	if (!m_module_id || error.type() == "no_suitable_module")
		return;

	auto query = sbin::DB()->Query("SELECT name FROM processingmodule WHERE id=" + str::Str(m_module_id));
	string pm_name = query->AsString("name");
	int pm_id = m_module_id;
	string errortype = type;

	if (error.type() == "client" && error.object() == "bad_response" && m_module_data["url"] != error.value()) {
		Trace("Change problem type");
		string sql = "SELECT * FROM nameserver WHERE url = " + sbin::DB()->EscapeValue(error.value());
		auto query = sbin::DB()->Query(sql);
		if (!query->Eof()) {
			errortype = PROBLEM_NAMESERVER_CONNECT;
		} else {
			sql = "SELECT * FROM ipmgr WHERE url = " + sbin::DB()->EscapeValue(error.value());
			query = sbin::DB()->Query(sql);
			if (!query->Eof())
				errortype = PROBLEM_IPMGR_CONNECT;
		}
		if (!query->Eof()) {
			pm_name = query->AsString("name");
			pm_id = query->AsInt("id");
		}
	}

	string add_params;
	auto param_map = str::SplitParams(params);
	ForEachI(param_map, p) {
		add_params += "&param_" + p->first + "=" + str::url::Encode(p->second);
	}


	sbin::ClientQuerySafe("func=problems.register&name=" + str::url::Encode(errortype) +
						"&id=" + str::Str(pm_id) +
						"&param_pm_name=" + str::url::Encode(pm_name) +
						"&param_pm_id=" + str::Str(pm_id) +
						"&param_errormsg=" + str::url::Encode(error.what()) +
						add_params +
						"&sok=ok&level=error");
}

void Module::AddTldParam(StringMap &params, const int iid) {
	mgr_db::QueryPtr q_tld = sbin::DB()->Query("SELECT t.* FROM item i JOIN pricelist p ON i.pricelist = p.id JOIN tld t ON p.intname = t.id WHERE i.id = " + str::Str(iid));
	if (!q_tld->Eof()) {
		for (size_t i = 0; i < q_tld->ColCount(); ++i) {
			params["tld_" + q_tld->ColName(i)] = q_tld->AsString(i);
		}
	}
}

void Module::SetConfig(const int elid, mgr_xml::Xml &config) {
	sbin::ClientQuery("func=processing.setconfig&elid=" + str::Str(elid) + "&"
					"config=" + str::url::Encode(config.Str()));
}

mgr_xml::Xml Module::GetConfig(const int elid) {
	string config_str = sbin::DB()->Query("SELECT config FROM processingmodule WHERE id=" +
							 str::Str(elid))->AsString("config");
	mgr_xml::Xml config_xml;
	if(!config_str.empty())
		config_xml.LoadFromString(config_str);
	return config_xml;
}

void Module::SetManualRerun(const int runningoperation) {
	if (runningoperation)
		sbin::ClientQuerySafe("func=runningoperation.setmanual&elid=" + str::Str(runningoperation));
}

void Module::CreateTask(const int iid, const std::string &type, const std::string &params, const bool uniq) {
	SetManualRerun(str::Int(m_args->RunningOperation.AsString()));
	if (uniq) {
		const int task_count = sbin::DB()->Query("SELECT COUNT(*) FROM task WHERE type=" + sbin::DB()->EscapeValue(type) + " AND "
		                                         "item=" + str::Str(iid) + " AND status!=" + str::Str(table::tsClosed))->Int();
		if (task_count > 0)
			return;
	}
	string cmd = "func=task.edit&item=" + str::Str(iid) + "&type=" + type + "&sok=ok";
	if (m_args->RunningOperation.Exists)
		cmd += "&runningoperation=" + m_args->RunningOperation.AsString();
	if (!params.empty())
		cmd += "&params=" + str::url::Encode(params);
	sbin::ClientQuery(cmd);
}

}