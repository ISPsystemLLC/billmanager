#ifndef __UTIL_H__
#define __UTIL_H__

#include <mgr/mgrcrypto.h>
#include <mgr/mgrproc.h>
#include <mgr/mgrdb_struct.h>
#include <mgr/mgrclient.h>
#include "defines.h"

namespace util {

bool DoNothing();
string RandomString(const size_t len, const string& allowed_symbols = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz");
string DecryptValue(const string& keypath, const string& value);
double MeasureRelation(const string& from, const string& to, mgr_db::Connection* db, bool throw_exception = true);

}

namespace str {
  StringMap SplitParams(string params, const string& param_delimeter = "=", const string& line_delimeter = "&");
}

namespace sbin {

std::shared_ptr<mgr_db::Cache> DB();
mgr_client::Local & Client();
mgr_client::Result ClientQuery(const string &query);
mgr_client::Result ClientQuery(const string &func, const StringMap & params);
mgr_client::Result ClientQuerySafe(const string &query);
string BuildMgrQuery (const string & func, const StringMap & params);
string GetMgrConfParam(const string& name, const string& def_val = "");
// string GetMgrPath(const string& name, const string& def_val);
// bool HasMgrConfOption(const string& option);
void Init(const string module_name);
void Init(const string module_name, void (*SignalWatcher)(int));
// bool TermSignalRecieved();
// void SetTermSignalReceived();


}


#endif