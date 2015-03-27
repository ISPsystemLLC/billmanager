#!/usr/bin/php
<?php

set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "pmpaycgi");

require_once 'bill_util.php';

$longopts  = array
(
    "command:",
    "payment:",
    "amount:",
);

$options = getopt("", $longopts);

try {
	$command = $options['command'];
	Debug("command ". $options['command']);

	if ($command == "config") {
		$config_xml = simplexml_load_string($default_xml_string);
		$feature_node = $config_xml->addChild("feature");

		// $feature_node->addChild("refund", 			"on");
		// $feature_node->addChild("transfer", 		"on");
		$feature_node->addChild("redirect", 		"on");
		// $feature_node->addChild("noselect", 		"on");
		$feature_node->addChild("notneedprofile", 	"on");

		// $feature_node->addChild("pmtune", 			"on");
		// $feature_node->addChild("pmvalidate", 		"on");

		// $feature_node->addChild("crtune", 			"on");
		// $feature_node->addChild("crvalidate", 		"on");
		// $feature_node->addChild("crset", 			"on");
		// $feature_node->addChild("crdelete", 		"on");

		// $feature_node->addChild("rftune", 			"on");
		// $feature_node->addChild("rfvalidate", 		"on");
		// $feature_node->addChild("rfset", 			"on");

		// $feature_node->addChild("tftune", 			"on");
		// $feature_node->addChild("tfvalidate", 		"on");
		// $feature_node->addChild("tfset", 			"on");

		$param_node = $config_xml->addChild("param");

		$param_node->addChild("payment_script", 	"/mancgi/paycgipayment.php");

		echo $config_xml->asXML();
	// } elseif ($command == "") {
	} else {
		throw new Error("unknown command");
	}
} catch (Exception $e) {
	echo $e;
}

?>