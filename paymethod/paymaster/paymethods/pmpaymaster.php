#!/usr/bin/php
<?php

/**
 * Adding PHP include
 */
set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "pmpaymaster.php");

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

$rtMaxAmount = 8; /*Требует указания максимальной суммы за месяц*/
$rtRedirect	= 20; /*для подтверждения оплаты необходим редирект*/
$rtNeedInit	= 24; /*Для настройки сохр. способа оплаты необходимо получить токен отдельно от платежа. Невозможно сохранить карту при совершении платежа*/

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

		// $feature_node->addChild("pmtune", 		"on");
		// $feature_node->addChild("pmvalidate", 	"on");

		// $feature_node->addChild("crtune", 		"on"); 
		// $feature_node->addChild("crvalidate", 	"on");
		$feature_node->addChild("crset", 		"on");
		// $feature_node->addChild("crdelete", 		"on");

		// $feature_node->addChild("rftune", 		"on");
		// $feature_node->addChild("rfvalidate", 	"on");
		// $feature_node->addChild("rfset", 		"on");

		// $feature_node->addChild("tftune", 		"on");
		// $feature_node->addChild("tfvalidate", 	"on");
		// $feature_node->addChild("tfset", 		"on");

		$feature_node->addChild("recurring","on"); // If paymethod allow to Auto-Recharge
		$feature_node->addChild("stored", 	"on"); // If paymethod allow to save card token  
		$feature_node->addChild("rcpay", 	"on"); // If payment without acceptance is available
		$feature_node->addChild("rcdelete", "on"); // If delete card token is available 		

		$param_node = $config_xml->addChild("param");

		$param_node->addChild("payment_script", "/mancgi/paymasterpayment.php");
		$param_node->addChild("recurring_script", "/mancgi/paymasterrecurring.php");
		$param_node->addChild("recurring_type", (1 << $rtRedirect) + (1 << $rtNeedInit) + (1 << $rtMaxAmount));

		echo $config_xml->asXML();
	} elseif ($command == "rcpay") {
		$payment_id = $options['payment'];
		$payment_info = LocalQuery("payment.info", array("elid" => $payment_id));
		$recurring_info = LocalQuery("payment.recurring.info", array("elid" => $payment_info->payment->recurring));

		$out_json = MakePayment($payment_info, $recurring_info);
		
		if (ErrorExists($out_json)) {
			LocalQuery("payment.setcanceled", array("elid" => $payment_id));
		} else {
			$status =  GetPaymentStatus($payment_info, $recurring_info, $out_json->processor_transaction_id)->status;

			if ($status == "complete") {
				LocalQuery("payment.setpaid", array("elid" => $payment_id, ));
			} else if ($status == "in_progress") {
				LocalQuery("payment.setinpay", array("elid" => $payment_id, ));
			} else if ($status == "failure") {
				LocalQuery("payment.setcanceled", array("elid" => $payment_id, ));
			}			 
		}
	} elseif ($command == "rcdelete") {
		$recurring_id = $options['recurring'];
		$info = LocalQuery("payment.recurring.info", array("elid" => $recurring_id));

		$out = HttpQuery("https://paymaster.ru/direct/security/token",
						 MakePayload(
							array(
								"client_id" => $info->payment->paymethod->LMI_MERCHANT_ID,
								"access_token" => $info->recurring->token,
								"type" => "rest"),
							$info->payment->paymethod->secret),
						 "POST");
	} elseif ($command == "crset") {

	} else {
		throw new ISPErrorException("unknown command");
	}
} catch (Exception $e) {
	echo $e;
}

function GetPaymentStatus($payment_info, $recurring_info, $processor_transaction_id) {
	$param = array(
		"access_token" => $recurring_info->recurring->token."",
		"merchant_id" => $payment_info->payment->paymethod[1]->LMI_MERCHANT_ID."",
		"merchant_transaction_id" => $payment_info->payment->id."",
		"processor_transaction_id" => $processor_transaction_id,
		"type" => "rest"
	);

	$out = HttpQuery("https://paymaster.ru/direct/payment/complete",
					MakePayload(
						$param,
						$payment_info->payment->paymethod[1]->secret.""),
					"POST");

	return json_decode($out);
}

function ErrorExists($out_json) {
    return property_exists($out_json, "error");
}

function MakePayment($payment_info, $recurring_info) {
	$param = array(
		"access_token" => $recurring_info->recurring->token."",
		"merchant_id" => $payment_info->payment->paymethod[1]->LMI_MERCHANT_ID."",
		"merchant_transaction_id" => $payment_info->payment->id."",
		"amount" => $payment_info->payment->paymethodamount."",
		"currency" => $payment_info->payment->currency[1]->iso."",
		"description" => $payment_info->payment->description."",
		"type" => "rest"
	);

	$out = HttpQuery("https://paymaster.ru/direct/payment/init",
					MakePayload(
						$param,
						$payment_info->payment->paymethod[1]->secret.""),
					"POST");

	return json_decode($out);
}

function MakePayload($param, $secret_key)
{	
	$iat = time();
	$sign = base64_encode(hash('sha256', http_build_query($param).';'.$iat.";".$secret_key, true));

	$param["iat"] = $iat;
	$param["sign"] = $sign;

	return $param;
}
?>