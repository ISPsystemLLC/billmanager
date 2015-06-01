#include "util.h"
#include <mgr/mgrlog.h>
#include <mgr/mgrproc.h>
#include <mgr/mgrenv.h>
#include <signal.h>
#include <strings.h>
#include <algorithm>

MODULE ("util");

struct MeasureRel {
	int Relation;
	string child;
	MeasureRel(const int relation, const string& child_intname): Relation(relation), child(child_intname) {}
	MeasureRel(): Relation(0) {}
};

std::map<std::string, MeasureRel> GetMeasureMap(mgr_db::Connection* db) {
	std::map<string, MeasureRel> MeasureMap;
	ForEachQuery(db, "SELECT m1.intname as cur_measure, m1.relation, "
				"m2.intname AS less_measure "
				"FROM measure m1 left join measure m2 on m1.lessmeasure=m2.id", meas) {
		MeasureMap.insert(std::make_pair(meas->AsString("cur_measure"), MeasureRel(meas->AsInt("relation"), meas->AsString("less_measure"))));
	}

	return MeasureMap;
}

namespace util {

bool DoNothing() {return mgr_file::Exists("etc/" MGR_NAME "." DO_NOTHING );}

string RandomString(const size_t len, const string& allowed_symbols) {
	const string random_bin(str::Random(len));
	string random_str(len, '0');
	for(size_t i = 0; i < len; ++i)
		random_str[i] = allowed_symbols[random_bin[i] % allowed_symbols.size()];
	return random_str;
}

string DecryptValue(const string &keypath, const string &value) {
	if (value.empty())
		return value;
	auto key = mgr_crypto::pem_private::Decode(mgr_file::Read(keypath));
	return mgr_crypto::crypt::Decrypt(key, str::base64::Decode(value));
}

double MeasureRelation(const string &from, const string &to, mgr_db::Connection* db, bool throw_exception) {
	double rel = 1.0f;

	std::map<string, MeasureRel> MeasureMap = GetMeasureMap(db);
	string curr = from;

	const int max_steps = 50;
	int i = 0;
	while (!MeasureMap[curr].child.empty() && curr != to) {
		rel *= MeasureMap[curr].Relation;
		curr = MeasureMap[curr].child;

		++i;
		ASSERT(i < max_steps, "MeasureRelation::max_steps");
	}
	if (curr == to)
		return rel;
	rel = 1;
	curr = to;
	while (!MeasureMap[curr].child.empty() && curr != from) {
		ASSERT(MeasureMap[curr].Relation != 0, "MeasureRelation: div zero");
		rel /= MeasureMap[curr].Relation;
		curr = MeasureMap[curr].child;
		++i;
		ASSERT(i < max_steps, "MeasureRelation::max_steps");
	}

	if (curr == from)
		return rel;

	if (throw_exception)
		throw mgr_err::Error("not_found_relation_for_measure")
			.add_param("from", from)
			.add_param("to", to);
	else return 0.0f;
}

}

namespace str {
	
StringMap SplitParams(string params, const string& param_delimeter, const string& line_delimeter) {
	StringMap result;
	  string line;
	  while (!(line = str::GetWord(params, line_delimeter)).empty()) {
		  Debug("line: %s", line.c_str());
		  str::inpl::Trim(line);
		  string name = str::GetWord(line, param_delimeter);
		  str::inpl::Trim(name);
		  str::inpl::Trim(line);

		  result[name] = str::url::Decode(line);
	}

	return result;
}

}

namespace sbin {

static string ModuleName = "sbinutils";
static bool bTermSignalRecieved = false;

string BuildMgrQuery (const string & func, const StringMap & params) {
	string result="func=" + func;
	ForEachI(params, param) {
		result += "&" + param->first + "=" + param->second;
	}
	return result;
}
	
mgr_client::Local & Client() {
	static mgr_client::Local client (MGR, ModuleName);
	return client;
}
	
mgr_client::Result ClientQuery(const string &query) {
	LogInfo ("QUERY: %s", query.c_str ());
	mgr_client::Result result = Client().Query (query);
	Debug ("QUERY_RESULT: \n%s", result.xml.Str (true).c_str ());
	return result;
}

mgr_client::Result ClientQuery(const string &func, const StringMap & params) {
	return ClientQuery(BuildMgrQuery(func, params));
}

std::shared_ptr<mgr_db::Cache> DB() {
	static bool initialized = false;
	static std::shared_ptr<mgr_db::Cache> db;
	static mgr_db::ConnectionParams params;
	if (!initialized) {
		Debug ("Initialize db");
		initialized = true;

		params.type = "mysql";
		params.host = GetMgrConfParam(ConfDBHost, DefaultDBHost);
		params.user = GetMgrConfParam(ConfDBUser, DefaultDBUser);
		params.password = GetMgrConfParam(ConfDBPassword);
		params.db = GetMgrConfParam(ConfDBName, DefaultDBName);
		if (!GetMgrConfParam(ConfDBSocket).empty())
			params.unix_socket = GetMgrConfParam(ConfDBSocket);

		db.reset(new mgr_db::JobCache(params));
	}
	return db;
}

mgr_client::Result ClientQuerySafe(const string &query) {
	int step = 1;
	mgr_date::DateTime start_time;
	while(1) {
		try {
			return sbin::ClientQuery(query);
		} catch (const mgr_err::Error& e) {
			if (e.type() == "client" && e.object() == "open" && e.value() == MGR) {
				++step;
				Warning("Could not establish a local connection to %s, try to repeat (try %d)", string(MGR).c_str(), step);
				if (mgr_date::DateTime() - start_time < QUERY_REPEAT_TIMEOUT) {
					mgr_proc::Sleep(1000);
					continue;
				}
			}
			throw;
		}
	}
}

string GetMgrConfParam(const string& name, const string& def_val) {
	static bool initialized = false;
	static StringMap params;
	if (!initialized) {
		auto paramList = ClientQuery ("out=xml&func=otparamlist").xml;
		mgr_xml::XPath xpath = paramList.GetNodes ("/doc/elem");
		ForEachI(xpath, elem) {
			mgr_xml::XmlNode childNode = elem->FirstChild ();
			params[childNode.Name ()] = childNode.Str ();
		}
		initialized = true;
	}
	string res = params[name];
	if (res.empty())
		res = def_val;
	return res;
}

void AddPath(string& env_path, const string& path) {
	if (mgr_file::Exists(path) && env_path.find(path) == string::npos) str::inpl::Append(env_path, path, ":");
}

void Init(const string module_name, void (*SignalWatcher)(int)) {
	ModuleName = module_name;
	mgr_log::Init(module_name);

	LogExtInfo("Set signal hanlers");
	struct sigaction sa;
	bzero(&sa, sizeof(sa));
	sigaddset(&sa.sa_mask, SIGTERM);
	sigaddset(&sa.sa_mask, SIGINT);
	sa.sa_handler = SignalWatcher;
	sa.sa_flags = SA_RESTART;
	sigaction(SIGTERM, &sa, 0);
	sigaction(SIGINT, &sa, 0);
	signal(SIGPIPE, SIG_IGN);
	signal(SIGCHLD, SIG_DFL);

	string env_path = mgr_env::GetEnv("PATH");
	AddPath(env_path, "/usr/local/sbin");
	AddPath(env_path, "/usr/sbin");
	AddPath(env_path, "/sbin");
	mgr_env::SetEnv("PATH", env_path);
}

static void TermSignal(int sig) {
	LogInfo("Signal %d recieved. Preparing to stop", sig);
	bTermSignalRecieved = true;
}

void Init(const string module_name) {
	Init (module_name, TermSignal);
}

}

