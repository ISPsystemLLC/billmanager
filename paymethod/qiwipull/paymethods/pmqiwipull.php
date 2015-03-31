#!/usr/bin/php
<?php

/**
 * Adding PHP include
 */
set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "pmqiwipull");

require_once 'bill_util.php';

/**
 * [$longopts description]
 * @var array
 */
$longopts  = array
(
    "command:",
    "payment:",
    "amount:",
);

$options = getopt("", $longopts);

/**
 * Processing --command
 */
try {
	$command = $options['command'];
	Debug("command ". $options['command']);

	if ($command == "config") {
		$config_xml = simplexml_load_string($default_xml_string);
		$feature_node = $config_xml->addChild("feature");

		// $feature_node->addChild("refund", 		"on"); // If refund supported
		// $feature_node->addChild("transfer", 		"on"); // If transfer supported
		$feature_node->addChild("redirect", 		"on"); // If redirect supported
		// $feature_node->addChild("noselect", 		"on"); // If noselect supported
		$feature_node->addChild("notneedprofile", 	"on"); // If notneedprofile supported

		$feature_node->addChild("pmtune", 			"on");
		$feature_node->addChild("pmvalidate", 		"on");

		// $feature_node->addChild("crtune", 			"on");
		$feature_node->addChild("crvalidate", 		"on");
		$feature_node->addChild("crset", 			"on");
		$feature_node->addChild("crdelete", 		"on");

		// $feature_node->addChild("rftune", 			"on");
		// $feature_node->addChild("rfvalidate", 		"on");
		// $feature_node->addChild("rfset", 			"on");

		// $feature_node->addChild("tftune", 			"on");
		// $feature_node->addChild("tfvalidate", 		"on");
		// $feature_node->addChild("tfset", 			"on");

		$param_node = $config_xml->addChild("param");

		$param_node->addChild("payment_script", "/mancgi/qiwipullpayment.php");

		echo $config_xml->asXML();
	} elseif ($command == "pmtune") {
		$paymethod_form = simplexml_load_string(file_get_contents('php://stdin'));
		$pay_source = $paymethod_form->addChild("slist");
		$pay_source->addAttribute("name", "pay_source");
		$pay_source->addChild("msg", "qw");
		$pay_source->addChild("msg", "mobile");
		echo $paymethod_form->asXML();
	} elseif ($command == "pmvalidate") {
		$paymethod_form = simplexml_load_string(file_get_contents('php://stdin'));
		Debug($paymethod_form->asXML());

		$API_ID = $paymethod_form->API_ID;
		$PRV_ID = $paymethod_form->PRV_ID;

		Debug($API_ID);
		Debug($PRV_ID);

		if (!preg_match("/^\d+$/", $API_ID)) {
			throw new Error("value", "API_ID", $API_ID);
		}

		if (!preg_match("/^\d+$/", $PRV_ID)) {
			throw new Error("value", "PRV_ID", $PRV_ID);
		}

		echo $paymethod_form->asXML();
	} elseif ($command == "crdelete") {
		$payment_id = $options['payment'];
		$info = LocalQuery("payment.info", array("elid" => $payment_id, ));

		$out = HttpQuery("https://qiwi.com/api/v2/prv/" . $info->payment[0]->paymethod[1]->PRV_ID . "/bills/" . $payment_id,
						 array("status" => "rejected"),
						 "PATCH",
						 $info->payment[0]->paymethod[1]->API_ID,
						 $info->payment[0]->paymethod[1]->API_PASSWORD);

		$out_xml = simplexml_load_string($out);
		if ($out_xml->result_code == "0" || $out_xml->result_code == "210") {
			LocalQuery("payment.delete", array("elid" => $payment_id, ));
		}
	} elseif ($command == "crvalidate") {
		$payment_form = simplexml_load_string(file_get_contents('php://stdin'));

		$ok = $payment_form->addChild("ok", "/mancgi/qiwipullpayment.php?elid=" . $payment_form->payment_id);
		$ok->addAttribute("type", "5");

		echo $payment_form->asXML();
	} elseif ($command == "crset") {
		$payment_id = $options['payment'];
		$info = LocalQuery("payment.info", array("elid" => $payment_id, ));

		$phone = (string)$info->payment[0]->phone;
		$phone = preg_replace('/[^0-9]/', '', $phone);

		$lifetime = new DateTime;
		if ($info->payment[0]->paymethod[1]->autoclearperiod != "") {
			$lifetime->add(new DateInterval("P". $info->payment[0]->paymethod[1]->autoclearperiod ."D"));
		} else {
			$lifetime->add(new DateInterval("P30D"));
		}

		$input = array( "user" => "tel:+" . $phone,
				 		"amount" => (string)$info->payment[0]->paymethodamount,
				 		"ccy" => (string)$info->payment[0]->currency[1]->iso,
				 		"pay_source" => (string)$info->payment[0]->paymethod[1]->pay_source,
				 		"prv_name" => (string)$info->payment[0]->project->name,
				 		"comment" => (string)$info->payment[0]->number,
				 		"lifetime" => $lifetime->format("Y-m-d\TH:i:s"),);

		Debug(print_r($input, true));

		$out = HttpQuery("https://qiwi.com/api/v2/prv/" . $info->payment[0]->paymethod[1]->PRV_ID . "/bills/" . $payment_id,
						 $input,
						 "PUT",
						 $info->payment[0]->paymethod[1]->API_ID,
						 $info->payment[0]->paymethod[1]->API_PASSWORD);

		$out_xml = simplexml_load_string($out);
		if ($out_xml->result_code == "0") {
			LocalQuery("payment.setinpay", array("elid" => $payment_id, ));
		} else {
			throw new Error("payment_process_error", "", "", array("error_msg" => $out_xml->description));
		}
	} else {
		throw new Error("unknown command");
	}
} catch (Exception $e) {
	echo $e;
}

?>