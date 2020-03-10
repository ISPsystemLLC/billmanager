#!/usr/bin/php
<?php

/**
 * Example of domain registration module used connection to database.
 * All domains are virtual and stored in MySQL DB provided by settings
 */
/**
 * Adding PHP include
 */
set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "pmregistrar");

require_once 'bill_util.php';

/**
 * [$longopts description]
 * @var array
 */
$longopts  = array
(
    "command:",
    "subcommand:",
    "id:",
    "item:",
    "lang:",
    "module:",
    "itemtype:",
    "intname:",
    "param:",
    "value:",
    "runningoperation:",
    "level:",
    "addon:",
// registrar specific
    "tld:",
    "searchstring:",
);

$options = getopt("", $longopts);

function GetConnection() {
	$param = LocalQuery("paramlist", array());
	$result = $param->xpath('//elem/*');

	$param_map = array();
	$param_map["DBHost"] = "localhost";
	$param_map["DBUser"] = "root";
	$param_map["DBPassword"] = "";
	$param_map["DBName"] = "billmgr";

	while(list( , $node) = each($result)) {
	    $param_map[$node->getName()] = $node;
	}

	return new DB($param_map["DBHost"], $param_map["DBUser"], $param_map["DBPassword"], $param_map["DBName"]);
}

function ItemParam($db, $iid) {
	$res = $db->query("SELECT i.id AS item_id, i.processingmodule AS item_module, i.period AS item_period, i.status AS item_status, i.expiredate, 
							  tld.name AS tld_name 
					   FROM item i 
					   JOIN pricelist p ON p.id = i.pricelist 
					   JOIN tld ON tld.id = p.intname 
					   WHERE i.id=" . $iid);

	if ($res == FALSE)
		throw new ISPErrorException("query", $db->error);

    $param = $res->fetch_assoc();

    $param_res = $db->query("SELECT intname, value FROM itemparam WHERE item = ".$iid);
    while ($row = $param_res->fetch_assoc()) {
    	$param[$row["intname"]] = $row["value"];
    }

    return $param;
}

function ItemProfiles($db, $iid, $module) {
	$param = array();
	$res = $db->query("SELECT sp2i.service_profile AS service_profile, sp2i.type AS type, sp2p.externalid AS externalid, sp2p.externalpassword AS externalpassword 
					   FROM item i 
					   JOIN service_profile2item sp2i ON sp2i.item = i.id 
					   LEFT JOIN service_profile2processingmodule sp2p ON sp2p.service_profile = sp2i.service_profile AND sp2i.type = sp2p.type AND sp2p.processingmodule = " . $module . "
					   WHERE i.id=" . $iid);
	while ($row = $res->fetch_assoc()) {
    	$param[$row["type"]] = array();
    	$param[$row["type"]]["externalid"] = $row["externalid"];
    	$param[$row["type"]]["externalpassword"] = $row["externalpassword"];
    	$param[$row["type"]]["service_profile"] = $row["service_profile"];

    	$profile_res = $db->query("SELECT intname, value 
					   FROM service_profileparam 
					   WHERE service_profile=" . $row["service_profile"]);

    	while ($profile_row = $profile_res->fetch_assoc()) {
    		$param[$row["type"]][$profile_row["intname"]] = $profile_row["value"];
    	}
    }

    return $param;
}

function GetDomainConnection($sid) {
	if ($sid != "") {
		$param = LocalQuery("processing.edit", array("elid" => $sid));
		return new DB($param->dbhost, $param->username, $param->password, $param->dbname);
	} else {
		return new DB("localhost", "root", "1", "domains"); // temporary default connection
	}
}

try {
	$command = $options['command'];
	$runningoperation = array_key_exists("runningoperation", $options) ? (int)$options['runningoperation'] : 0;
	$item = array_key_exists("item", $options) ? (int)$options['item'] : 0;

	Debug("command ". $options['command'] . ", item: " . $item . ", operation: " . $runningoperation);

	if ($command == "features") {
		/**
		 * Build and output XML with module features and configuration
		 */
		$config_xml = simplexml_load_string($default_xml_string);

		/**
		 * Set supported itemtype 'domain'
		 */
		$itemtypes_node = $config_xml->addChild("itemtypes");
		$itemtypes_node->addChild("itemtype")->addAttribute("name", "domain");

		/**
		 * Set settings param
		 */
		$params_node = $config_xml->addChild("params");
		$params_node->addChild("param")->addAttribute("name", "registrar_name"); 				// Name of registrar
		$params_node->addChild("param")->addAttribute("name", "whois_lang");					// Language of WHOIS response4
		$params_node->addChild("param")->addAttribute("name", "username");						// Username for DB connection

		$password = $params_node->addChild("param");											// Password for DB connection
		$password->addAttribute("name", "password");
		$password->addAttribute("crypted", "yes");

		$params_node->addChild("param")->addAttribute("name", "dbname");						// Name of DB
		$params_node->addChild("param")->addAttribute("name", "dbhost");						// DB server host

		/**
		 * Set supported features. Any feature can be skipped
		 */
		$features_node = $config_xml->addChild("features");
		$features_node->addChild("feature")->addAttribute("name", "check_connection");			// Checking connection to DB with provided credentials
		$features_node->addChild("feature")->addAttribute("name", "tune_connection");			// Tune connection form
		$features_node->addChild("feature")->addAttribute("name", "import");					// Import service from DB
		$features_node->addChild("feature")->addAttribute("name", "open");						// Register new domains in DB
		$features_node->addChild("feature")->addAttribute("name", "suspend");					// Suspend domain. Simple change status
		$features_node->addChild("feature")->addAttribute("name", "resume");					// Resume domain. Simple change status
		$features_node->addChild("feature")->addAttribute("name", "close");						// Delete domain. Delete from DB and set status
		$features_node->addChild("feature")->addAttribute("name", "cancel_prolong");			// Cancel auto prolong of domains
		$features_node->addChild("feature")->addAttribute("name", "setparam");					// Change param of service. Usually not used for domains
		$features_node->addChild("feature")->addAttribute("name", "prolong");					// Prolong service. Simple chnage expiredate of domain in DB
		$features_node->addChild("feature")->addAttribute("name", "transfer");					// Transfer domain from other registrar. Like 'open', but transfer
		$features_node->addChild("feature")->addAttribute("name", "sync_item");					// Get actual info about service
		$features_node->addChild("feature")->addAttribute("name", "get_contact_type");			// Get contact type needed for TLD and other specific TLD parameters
		$features_node->addChild("feature")->addAttribute("name", "tune_service_profile");		// Tune service profile (domain contact) form while order service
		$features_node->addChild("feature")->addAttribute("name", "validate_service_profile");  // Validate provided by customer basic or additional service profile parameters
		$features_node->addChild("feature")->addAttribute("name", "update_ns");					// Change list of domain nameserver
		$features_node->addChild("feature")->addAttribute("name", "whois");						// Return WHOIS domain data. Used by BILLmanager for checking domain availability and in lists

		echo $config_xml->asXML();
	} elseif ($command == "tune_connection") {
		// Add whois_lang select for 'ru' or 'en'
		$connection_form = simplexml_load_string(file_get_contents('php://stdin'));
		$lang = $connection_form->addChild("slist");
		$lang->addAttribute("name", "whois_lang");
		$lang->addChild("msg", "ru");
		$lang->addChild("msg", "en");
		echo $connection_form->asXML();
	} elseif ($command == "check_connection") {
		$connection_param = simplexml_load_string(file_get_contents('php://stdin'));
		$registrar_name = $connection_param->processingmodule->registrar_name;
		$password = $connection_param->processingmodule->password;
		$username = $connection_param->processingmodule->username;
		$dbname = $connection_param->processingmodule->dbname;
		$dbhost = $connection_param->processingmodule->dbhost;

		// Check access to DB with domans
		try {
			new DB($dbhost, $username, $password, $dbname);
		} catch (Exception $e) {
			throw new ISPErrorException("invalid_login_or_passwd");
		}

		echo $default_xml_string;
	} elseif ($command == "get_contact_type") {
		/**
		 * Return XML config for TLD
		 */

		$config_xml = simplexml_load_string($default_xml_string);
		$tld = $options['tld'];
		if ($tld == "my") { // TLD with all available options
			$config_xml->addAttribute("auth_code", "require");			// Require authentificate code while order domain transfer of 'my' tld 
			$config_xml->addAttribute("ns", "require");				// Require NS while order or transfer domain of 'my' tld
			$config_xml->addAttribute("cancel_prolong_before", "30");	// Execute cancel_prolong command for domain before 30 day of expire
		}
		$config_xml->addChild("contact_type", "customer"); 	// Contact for customer account. Usually used for registrar with creating acconut for your customer
		$config_xml->addChild("contact_type", "owner");		// Owner contact
		$config_xml->addChild("contact_type", "admin");		// Administrativ contact
		$config_xml->addChild("contact_type", "bill");		// Billing contact
		$config_xml->addChild("contact_type", "tech");		// Technical contact

		echo $config_xml->asXML();
	} elseif ($command == "whois") {
		/**
		 * Show whois data. Only if need self whois service
		 */
		$domain = $options['param'];

		$whois_xml = simplexml_load_string($default_xml_string);

		$ddb = GetDomainConnection($options["module"]);
		if ($ddb->query("SELECT COUNT(*) FROM domain WHERE status != 'deleted' AND name = '" . $ddb->real_escape_string($domain) . "'")->fetch_row()[0] == 0) {
			$whois_xml->addChild("whois", "not exist");
		} else {
			$whois = "Domain: " . $domain . "\n";
			$param = $ddb->query("SELECT * FROM domain WHERE name = '" . $ddb->real_escape_string($domain) . "' AND status != 'deleted'")->fetch_assoc();
			$whois .= "Expiredate: " . $param["expiredate"] . "\n";
			$whois .= "Name servers: " . $param["ns"] . "\n";
			$whois .= "Status: " . $param["status"] . "\n";
			$whois .= "Description: " . $param["description"] . "\n";
			$whois_xml->addChild("whois", $whois);
		}

		echo $whois_xml->asXML();
	} elseif ($command == "tune_service_profile") {
		/**
		 * Tune service profile create form
		 */
		$tld = $options['param'];
		$contact_type = $options['value'];

		$service_profile_form = simplexml_load_string(file_get_contents('php://stdin'));

		if ($tld == "my" && $contact_type == "customer") {
			Debug("Add usage select");

			$select = $service_profile_form->addChild("slist");
			$select->addAttribute("name", "customer_my_usage");
			$select->addChild("msg", "my_usage_personal")->addAttribute("key", "personal");
			$select->addChild("msg", "my_usage_company")->addAttribute("key", "company");
		}

		echo $service_profile_form->asXML();
	} elseif ($command == "validate_service_profile") {
		/**
		 * Example of service profile validate. Check if agree checked
		 */
		$param_xml = simplexml_load_string(file_get_contents('php://stdin'));

		$tld = $options['param'];

		if ($tld == "my" && $param_xml->customer_my_agree != "on")
			throw new ISPErrorException("customer_agree", "customer_my_agree");

	} elseif ($command == "open" || $command == "transfer") {
		// Check if domain ixist in database and create it

		$db = GetConnection();

		$iid = $options['item'];
		$item_param = ItemParam($db, $iid);

		$ddb = GetDomainConnection($item_param["item_module"]);

		if ($ddb->query("SELECT COUNT(*) FROM domain WHERE status != 'deleted' AND name = '" . $ddb->real_escape_string($item_param["domain"]) . "'")->fetch_row()[0] > 0)
			throw new ISPErrorException("exist");

		// Add service profiles into test DB (in real world send API requests to registrar)
		$profile_params = ItemProfiles($db, $iid, $item_param["item_module"]);
		$profile_external_link = array();

		foreach ($profile_params as $type => $param) {
			$externalid = $param["externalid"];
			$externalpassword = $param["externalpassword"];

			if ($externalid == "") {
				if (in_array($param["service_profile"], $profile_external_link)) {
					$externalid = $profile_external_link[$param["service_profile"]];
				} else {
					// Save profile in domains DB or call registrar API function
					$externalid = RandomStr();
					$externalpassword = RandomStr();

					if ($ddb->query("INSERT INTO contact (id, password, firstname, middlename, lastname) 
								 VALUES ('". $ddb->real_escape_string($externalid) ."',
								 	     '". $ddb->real_escape_string($externalpassword) ."',
								 	     '". $ddb->real_escape_string($param["firstname"]) ."',
								 	     '". $ddb->real_escape_string($param["middlename"]) ."',
								 	     '". $ddb->real_escape_string($param["lastname"]) ."')")) {
						LocalQuery("service_profile2processingmodule.edit", array("processingmodule" => $item_param["item_module"], 
																				  "service_profile" => $param["service_profile"],
																				  "type" => $type,
																				  "externalid" => $externalid,
																				  "externalpassword" => $externalpassword,
																				  "sok" => "ok", ));
					} else {
						throw new ISPErrorException("query", $db->error);
					}
				}

				$profile_external_link[$param["service_profile"]] = $externalid;
			}

			$profile_params[$type]["externalid"] = $externalid;
		}

		$ns = "";
		$ns_num = 0;
		while (array_key_exists("ns" . $ns_num, $item_param)) {
			$ns .= $item_param["ns" . $ns_num] . " ";
			$ns_num++;
		}

		// Add domain into test DB (in real world send API requests to registrar)
		if ($ddb->query("INSERT INTO domain (name, status, customer, owner, admin, bill, tech, expiredate, ns, description) 
								 VALUES ('". $ddb->real_escape_string($item_param["domain"]) ."',
								 	     'active',
								 	     '". $ddb->real_escape_string($profile_params["customer"]["externalid"]) ."',
								 	     '". $ddb->real_escape_string($profile_params["owner"]["externalid"]) ."',
								 	     '". $ddb->real_escape_string($profile_params["admin"]["externalid"]) ."',
								 	     '". $ddb->real_escape_string($profile_params["bill"]["externalid"]) ."',
								 	     '". $ddb->real_escape_string($profile_params["tech"]["externalid"]) ."',
								 	     DATE_ADD(NOW(), INTERVAL " . $item_param["item_period"] . " MONTH),
								 	     '". $ddb->real_escape_string($ns) ."',
								 	     '". $ddb->real_escape_string(array_key_exists("domain_desc", $item_param) ? $item_param["domain_desc"] : "") ."')")) {
			// open service in BILLmanager
			LocalQuery("domain.open", array("elid" => $item, "sok" => "ok"));
		} else {
			throw new ISPErrorException("query", $db->error);
		}
	} elseif ($command == "suspend") {
		// Update status of domain in test DB. Suspend domain if possible via registrar API or cancel auto prolong if need
		$db = GetConnection();
		$iid = $options['item'];
		$item_param = ItemParam($db, $iid);
		$ddb = GetDomainConnection($item_param["item_module"]);

		$ddb->query("UPDATE domain SET status = 'suspend' WHERE name = '" . $ddb->real_escape_string($item_param["domain"]) . "' AND status != 'deleted'");

		// set service status to 'suspended' and delete running operation
		LocalQuery("service.postsuspend", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "resume") {
		// Update status of domain in test DB. Resume domain if possible via registrar API or enable auto prolong if need
		$db = GetConnection();
		$iid = $options['item'];
		$item_param = ItemParam($db, $iid);
		$ddb = GetDomainConnection($item_param["item_module"]);

		$ddb->query("UPDATE domain SET status = 'active' WHERE name = '" . $ddb->real_escape_string($item_param["domain"]) . "' AND status != 'deleted'");

		// set service status to 'active' and delete running operation
		LocalQuery("service.postresume", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "close") {
		// Update status of domain in test DB. Delete domain if possible via registrar API and disable auto prolong if need
		$db = GetConnection();
		$iid = $options['item'];
		$item_param = ItemParam($db, $iid);
		$ddb = GetDomainConnection($item_param["item_module"]);

		$ddb->query("UPDATE domain SET status = 'deleted' WHERE name = '" . $ddb->real_escape_string($item_param["domain"]) . "' AND status != 'deleted'");

		// set service status to 'deleted' and delete running operation
		LocalQuery("service.postclose", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "setparam") {
		// No example at now
		// delete running operation
		LocalQuery("service.postsetparam", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "prolong") {
		$db = GetConnection();
		$iid = $options['item'];
		$item_param = ItemParam($db, $iid);
		$ddb = GetDomainConnection($item_param["item_module"]);

		$expiredate = $ddb->query("SELECT GREATEST(expiredate, NOW()) FROM domain WHERE name = '" . $ddb->real_escape_string($item_param["domain"]) . "' AND status != 'deleted'")->fetch_row()[0];
		$ddb->query("UPDATE domain SET status = 'active', expiredate = DATE_ADD('" . $expiredate . "', INTERVAL " . $item_param["item_period"] . " MONTH) WHERE name = '" . $ddb->real_escape_string($item_param["domain"]) . "' AND status != 'deleted'");

		// delete running operation
		LocalQuery("service.postprolong", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "cancel_prolong") {
		// No example at now
		// Cancel auto prolong for domain via registrar API if need for provided tld
	} elseif ($command == "sync_item") {
		// Get domain info from registrar and update in BILLmanager.
		$db = GetConnection();
		$iid = $options['item'];
		$item_param = ItemParam($db, $iid);
		$ddb = GetDomainConnection($item_param["item_module"]);

		$param = $ddb->query("SELECT * FROM domain WHERE name = '" . $ddb->real_escape_string($item_param["domain"]) . "' AND status != 'deleted'")->fetch_assoc();
		if ($param["status"] == "active") {
			LocalQuery("service.postresume", array("elid" => $item, "sok" => "ok", ));
			LocalQuery("service.setstatus", array("elid" => $item, "service_status" => "2", ));
		} else {
			LocalQuery("service.postsuspend", array("elid" => $item, "sok" => "ok", ));
			LocalQuery("service.setstatus", array("elid" => $item, "service_status" => "8", ));
		}

		LocalQuery("service.setexpiredate", array("elid" => $item, "expiredate" => $param["expiredate"], ));
	} elseif ($command == "update_ns") {
		// Update domain NS via registrar API. In example simple set new NS
		$db = GetConnection();
		$iid = $options['item'];
		$item_param = ItemParam($db, $iid);
		$ddb = GetDomainConnection($item_param["item_module"]);

		$ns = "";
		$ns_num = 0;
		while (array_key_exists("ns" . $ns_num, $item_param)) {
			$ns .= $item_param["ns" . $ns_num] . " ";
			$ns_num++;
		}

		$ddb->query("UPDATE domain SET ns = '" . $ddb->real_escape_string($ns) . "' WHERE name = '" . $ddb->real_escape_string($item_param["domain"]) . "' AND status != 'deleted'");
	} elseif ($command == "import") {
		// Get list of domains and contact. Import into BILLmanager

		$module = $options['module'];
		$search = array_key_exists("searchstring", $options) ? $options['searchstring'] : "";

		$search_array = explode(" ", $search);

		$db = GetConnection();
		$ddb = GetDomainConnection($module);

		$sub_query = "";

		foreach ($search_array as $domain) {
			if ($domain == "")
				continue;

			if ($sub_query == "")
				$sub_query .= " AND name in (";
			else
				$sub_query .= ",";
			$sub_query .= "'" . $ddb->real_escape_string($domain) . "'";
		}

		if ($sub_query != "")
			$sub_query .= ")";

		$contact_array = array();
		$type_array = array("customer", "owner", "admin", "bill", "tech");

		Debug("sub_query: ". $sub_query);

		$res = $ddb->query("SELECT customer, owner, admin, bill, tech, name, status, expiredate, ns FROM domain WHERE status != 'deleted'" . $sub_query);

		while ($row = $res->fetch_assoc()) {
			$tld_name = explode(".", $row["name"], 2)[1];
			$tld_id = $db->query("SELECT id FROM tld WHERE name = '" . $db->real_escape_string($tld_name) . "'")->fetch_row()[0];

			$domain_param = array();
			$domain_param["sok"] = "ok";
			$domain_param["expiredate"] = $row["expiredate"];
			$domain_param["module"] = $module;
			$domain_param["status"] = $row["status"] == "active" ? "2" : "8";
			$domain_param["import_pricelist_intname"] = $tld_id;
			$domain_param["import_service_name"] = $row["name"];
			$domain_param["domain"] = $row["name"];

			$service_id = LocalQuery("processing.import.service", $domain_param)->service_id;

			foreach ($type_array as $type) {
				Debug($type);
				if (array_key_exists($row[$type], $contact_array) == false) {
					$contact = $ddb->query("SELECT * FROM contact WHERE id  = '" . $ddb->real_escape_string($row[$type]) . "'")->fetch_assoc();
					$contact_param = array();
					$contact_param["sok"] = "ok";
					$contact_param["type"] = $type;
					$contact_param["name"] = $contact["firstname"];
					$contact_param["module"] = $module;
					$contact_param["externalid"] = $row[$type];
					$contact_param["profiletype"] = "1";
					$contact_param["firstname"] = $contact["firstname"];
					$contact_param["middlename"] = $contact["middlename"];
					$contact_param["lastname"] = $contact["lastname"];
					$contact_param["firstname_locale"] = $contact["firstname"];
					$contact_param["middlename_locale"] = $contact["middlename"];
					$contact_param["lastname_locale"] = $contact["lastname"];
					$contact_param["passport"] = "";
					$contact_param["location_postcode"] = "";
					$contact_param["location_state"] = "";
					$contact_param["location_city"] = "";
					$contact_param["location_address"] = "";
					$contact_param["birth_date"] = "";
					$contact_param["location_country"] = "";
					$contact_param["postal_postcode"] = "";
					$contact_param["postal_state"] = "";
					$contact_param["postal_city"] = "";
					$contact_param["postal_address"] = "";
					$contact_param["postal_addressee"] = "";
					$contact_param["phone"] = "";
					$contact_param["fax"] = "";
					$contact_param["email"] = "";
					$contact_param["inn"] = "";
					$contact_param["mobile"] = "";
					$contact_param["company"] = "";
					$contact_param["company_locale"] = "";
					$contact_param["kpp"] = "";
					$contact_param["ogrn"] = "";

					$profile_id = LocalQuery("processing.import.profile", $contact_param)->profile_id;

					$contact_array[$row[$type]] = $profile_id;
				}

				LocalQuery("service_profile2item.edit", array("sok" => "ok", "service_profile" => $contact_array[$row[$type]], "item" => $service_id, "type" => $type));
			}
		}
	}
} catch (Exception $e) {
	if ($runningoperation > 0) {
		// save error message for operation in BILLmanager
		LocalQuery("runningoperation.edit", array("sok" => "ok", "elid" => $runningoperation, "errorxml" => $e,));

		if ($item > 0) {
			// set manual rerung
			LocalQuery("runningoperation.setmanual", array("elid" => $runningoperation,));

			// create task
			$task_type = LocalQuery("task.gettype", array("operation" => $command,))->task_type;
			if ($task_type != "") {
				LocalQuery("task.edit", array("sok" => "ok", "item" => $item, "runningoperation" => $runningoperation, "type" => $task_type, ));
			}
		}
	}

	echo $e;
}
