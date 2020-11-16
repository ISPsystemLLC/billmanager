#!/usr/bin/php
<?php

set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "paymasterpayment");

require_once 'bill_util.php';

DoResponse(CgiInput());


function DoResponse($param) {
	echo "Content-Type: text/html\n\n";
	
	if ($param["auth"] == "") {
		throw new ISPErrorException("no auth info");
	} else {
		$info = LocalQuery("payment.info", array("elid" => $param["elid"]));
	
		$input = array(
			"LMI_RESULT_URL" => $info->payment->manager_url."/mancgi/paymasterresult.php",
			"LMI_PAYMENT_NOTIFICATION_URL" => $info->payment->manager_url."/mancgi/paymasterresult.php",
	
			"LMI_MERCHANT_ID" => $info->payment->paymethod[1]->LMI_MERCHANT_ID,
			"LMI_PAYMENT_AMOUNT" => $info->payment->paymethodamount,
			"LMI_CURRENCY" => $info->payment->currency[1]->iso,
			"LMI_PAYMENT_NO" => $info->payment->id,
			"LMI_PAYMENT_DESC" => $info->payment->description,
			"LMI_PAYMENT_DESC_BASE64" => base64_encode($info->payment->description),
			"LMI_PAYMENT_METHOD" => "503"
		);
	
		echo BuildForm($input);
	}
}

function BuildForm($input) {
	return
		"<html>\n".
		"<head>\n".
		"	<meta http-equiv='Content-Type' content='text/html; charset=UTF-8' />\n".
		"	<link rel='shortcut icon' href='billmgr.ico' type='image/x-icon' />\n".
		"	<script language='JavaScript'>\n".
		"		function DoSubmit() {\n".
		"			document.paymasterform.submit();\n".
		"		}\n".
		"	</script>\n".
		"</head>\n".
		"<body onload='DoSubmit()'>\n".
		"	<form name='paymasterform' action='https://paymaster.ru/payment/init' method='post'>\n".	
		implode("\n", array_map(
			function ($v, $k) { return sprintf("    <input type='hidden' name='%s' value='%s'/>", $k, $v); },
			$input,
			array_keys($input)
		)).
		"	</form>\n".
		"</body>\n".
		"</html>\n";
	}

?>