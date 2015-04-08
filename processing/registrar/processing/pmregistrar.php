#!/usr/bin/php
<?php

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

try {
	$command = $options['command'];
	$runningoperation = array_key_exists("runningoperation", $options) ? (int)$options['runningoperation'] : 0;
	$item = array_key_exists("item", $options) ? (int)$options['item'] : 0;

	Debug("command ". $options['command'] . ", item: " . $item . ", operation: " . $runningoperation);

	if ($command == "features") {
		$config_xml = simplexml_load_string($default_xml_string);

		$itemtypes_node = $config_xml->addChild("itemtypes");
		$itemtypes_node->addChild("itemtype")->addAttribute("name", "domain");

		$params_node = $config_xml->addChild("params");
		$params_node->addChild("param")->addAttribute("name", "registrar_name");
		$params_node->addChild("param")->addAttribute("name", "whois_lang");
		$password = $params_node->addChild("param");
		$password->addAttribute("name", "password");
		$password->addAttribute("crypted", "yes");

		$features_node = $config_xml->addChild("features");

		$features_node->addChild("feature")->addAttribute("name", "check_connection");
		$features_node->addChild("feature")->addAttribute("name", "tune_connection");
		$features_node->addChild("feature")->addAttribute("name", "import");

		$features_node->addChild("feature")->addAttribute("name", "open");
		$features_node->addChild("feature")->addAttribute("name", "suspend");
		$features_node->addChild("feature")->addAttribute("name", "resume");
		$features_node->addChild("feature")->addAttribute("name", "close");
		$features_node->addChild("feature")->addAttribute("name", "setparam");
		$features_node->addChild("feature")->addAttribute("name", "prolong");
		$features_node->addChild("feature")->addAttribute("name", "transfer");

		$features_node->addChild("feature")->addAttribute("name", "sync_item");
		$features_node->addChild("feature")->addAttribute("name", "tune_service");

		$features_node->addChild("feature")->addAttribute("name", "get_contact_type");

		$features_node->addChild("feature")->addAttribute("name", "tune_service_profile");
		$features_node->addChild("feature")->addAttribute("name", "validate_service_profile");

		$features_node->addChild("feature")->addAttribute("name", "update_ns");
		$features_node->addChild("feature")->addAttribute("name", "whois");

		echo $config_xml->asXML();
	} elseif ($command == "check_connection") {
		$connection_param = simplexml_load_string(file_get_contents('php://stdin'));
		$registrar_name = $connection_param->processingmodule->registrar_name;
		$password = $connection_param->processingmodule->password;

		Debug("name: " . $registrar_name . ", password: " . $password);

		if ($password != "test") {
			throw new Error("value", "password", $password);
		}

		echo $default_xml_string;
	} elseif ($command == "tune_connection") {
		$connection_form = simplexml_load_string(file_get_contents('php://stdin'));
		$lang = $connection_form->addChild("slist");
		$lang->addAttribute("name", "whois_lang");
		$lang->addChild("msg", "ru");
		$lang->addChild("msg", "en");
		echo $connection_form->asXML();
	} elseif ($command == "import") {

	} elseif ($command == "open") {

		// open service in BILLmanager
		LocalQuery("domain.open", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "suspend") {

		// set service status to 'suspended' and delete running operation
		LocalQuery("service.postsuspend", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "resume") {

		// set service status to 'active' and delete running operation
		LocalQuery("service.postresume", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "close") {

		// set service status to 'deleted' and delete running operation
		LocalQuery("service.postclose", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "setparam") {

		// delete running operation
		LocalQuery("service.postsetparam", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "prolong") {

		// delete running operation
		LocalQuery("service.postprolong", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "transfer") {

		// open service in BILLmanager
		LocalQuery("domain.open", array("elid" => $item, "sok" => "ok", ));
	} elseif ($command == "sync_item") {

	} elseif ($command == "tune_service") {

	} elseif ($command == "get_contact_type") {

	} elseif ($command == "tune_service_profile") {

	} elseif ($command == "validate_service_profile") {

	} elseif ($command == "update_ns") {

	} elseif ($command == "whois") {

	}
} catch (Exception $e) {
	if ($runningoperation > 0) {
		// save error message for operation
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