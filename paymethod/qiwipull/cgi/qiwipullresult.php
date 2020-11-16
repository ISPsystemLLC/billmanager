#!/usr/bin/php
<?php

set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "qiwipullresult");

require_once 'bill_util.php';

echo "Content-Type: text/xml\n\n";

$param = CgiInput(true);

$status = $param["status"];
$error = $param["error"];
$amount = $param["amount"];
$iso = $param["ccy"];
$command = $param["command"];

$out_xml = simplexml_load_string("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<result/>\n");

$x_api_signature = $_SERVER["HTTP_X_API_SIGNATURE"];
$authorization = $_SERVER["HTTP_AUTHORIZATION"];
$authorization_array = explode(' ',$authorization);
$authorization = $authorization_array[1];

Debug("x_api_signature: " . $x_api_signature);
Debug("authorization: " . $authorization);

if ($x_api_signature == "") {
	$out_xml->addChild("result_code", "151");
	$out_xml->addChild("description", "empty signature");
} elseif ($authorization == "") {
	$out_xml->addChild("result_code", "150");
	$out_xml->addChild("description", "empty authorization");
} elseif ($param["bill_id"] == "") {
	$out_xml->addChild("result_code", "5");
	$out_xml->addChild("description", "empty elid");
} else {
	$info = LocalQuery("payment.info", array("elid" => $param["elid"], ));
	if ($authorization != base64_encode($info->payment[0]->paymethod[1]->PRV_ID . ":" . $info->payment[0]->paymethod[1]->NOTIFY_PASSWORD)) {
		$out_xml->addChild("result_code", "150");
		$out_xml->addChild("description", "bad auth info");
	} else {
		ksort($param);
		$signature_string = "";
		foreach ($param as $key => $val) {
			if ($signature_string != "") {
				$signature_string .= "|";
			}
			$signature_string .= $val;
		}
		$signature = base64_encode(hash_hmac("sha1", $signature_string, $info->payment[0]->paymethod[1]->NOTIFY_PASSWORD, true));
		if ($signature != $x_api_signature) {
			$out_xml->addChild("result_code", "151");
			$out_xml->addChild("description", "invalid signature");
		} else {
			if ($command == "bill") {
				if ($error == "0" && $amount == (string)$info->payment[0]->paymethodamount && $iso == (string)$info->payment[0]->currency[1]->iso) {
					if ($status == "paid") {
						LocalQuery("payment.setpaid", array("elid" => $param["bill_id"], ));
					} else if ($status == "waiting") {
						LocalQuery("payment.setinpay", array("elid" => $param["bill_id"], ));
					} else if ($status == "rejected" || $status == "unpaid" || $status == "expired") {
						LocalQuery("payment.setnopay", array("elid" => $param["bill_id"], ));
					}
					$out_xml->addChild("result_code", "0");
				} else {
					$out_xml->addChild("result_code", "5");
					$out_xml->addChild("description", "invalid data");
				}
			} else {
				$out_xml->addChild("result_code", "5");
				$out_xml->addChild("description", "invalid command");
			}
		}
	}
}

Debug("out: ". $out_xml->asXML());
echo $out_xml->asXML();
?>