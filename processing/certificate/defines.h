#ifndef __DEFINES_H__
#define __DEFINES_H__
//processing
#define PROCESSING_FEATURES "features"
#define PROCESSING_OPEN "open"
#define PROCESSING_SUSPEND "suspend"
#define PROCESSING_CANCEL_PROLONG "cancel_prolong"
#define PROCESSING_RESUME "resume"
#define PROCESSING_CLOSE "close"
#define PROCESSING_SETPARAM "setparam"
#define PROCESSING_PROLONG "prolong"
#define PROCESSING_PROLONG_ADDON "prolong_addon"
#define PROCESSING_GET_SUITABLE_MODULE "get_suitable_module"
#define PROCESSING_CHECK_CONNECTION "check_connection"
#define PROCESSING_SYNC_PRICELIST "sync_pricelist"
#define PROCESSING_SYNC_SERVER "sync_server"
#define PROCESSING_SYNC_IPLIST "sync_iplist"
#define PROCESSING_GET_SERVER_CONFIG "get_server_config"
#define PROCESSING_SYNC_ITEM "sync_item"
#define PROCESSING_REOPEN "reopen"
#define PROCESSING_STAT "stat"
#define PROCESSING_SERVICE_IMPORT "import"
#define PROCESSING_PRICELIST_IMPORT "import_pricelist"
#define PROCESSING_CHECK_PARAM "check_param"
#define PROCESSING_CHECK_ADDON "check_addon"
#define PROCESSING_GEN_KEY "gen_key"
#define PROCESSING_CONNECTION_FORM_TUNE "tune_connection"
#define PROCESSING_SERVICE_PROFILE_FORM_TUNE "tune_service_profile"
#define PROCESSING_SERVICE_PROFILE_VALIDATE "validate_service_profile"
#define PROCESSING_USERCREATE "usercreate"
#define PROCESSING_TUNING_PARAM "tuning_param"

//processing domain
#define PROCESSING_DOMAIN_UPDATE_NS "update_ns"
#define PROCESSING_DOMAIN_TRANSFER "transfer"

//processing certificate
#define PROCESSING_CERTIFICATE_APPROVER "approver"

#define PROBLEM_PROCESSINGMODULE_GETNEXTMODULE "processingmodule_getnextmodule"
#define PROBLEM_PROCESSINGMODULE_CONNECT "processingmodule_connect"
#define PROBLEM_NAMESERVER_CONNECT "nameserver_connect"
#define PROBLEM_IPMGR_CONNECT "ipmgr_connect"

#define SERVICE_STATUS "service_status"
#define SERVICE_ORDER_ID "custom_order_id"

#define ConfCryptKey "CryptKey"
#define DefaultCryptKey "etc/billmgr.pem"

#define TEMPLATE_WILDCARD		"wildcard"
#define TEMPLATE_WWW			"www"
#define TEMPLATE_MULTIDOMAIN	"multidomain"
#define TEMPLATE_IDN			"idn"
#define TEMPLATE_ORGINFO		"orginfo"
#define TEMPLATE_CODESIGN		"codesign"
#define TEMPLATE_CSRALTNAME			"csraltname"

#define CERTIFICATE_ALTNAME		"altname"
#define CERTIFICATE_OLDALTNAME		"old_altname"

#define MGR_NAME "billmgr"
#define DO_NOTHING "DoNothing"

//Время, в сек., в течение которого запускать запросы повторно при отстствии соединения
//(используется в ClientQuerySafe()
#define QUERY_REPEAT_TIMEOUT	86400

#define DefaultDBHost "localhost"
#define DefaultDBUser "root"
#define DefaultDBName "billmgr5"
#define DefaultCryptKey "etc/billmgr.pem"

#define ConfDBHost "DBHost"
#define ConfDBUser "DBUser"
#define ConfDBPassword "DBPassword"
#define ConfDBName "DBName"
#define ConfDBSocket "DBSocket"
#define ConfCryptKey "CryptKey"

#endif