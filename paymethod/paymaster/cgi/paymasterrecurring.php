#!/usr/bin/php
<?php

set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "paymasterrecurring");

require_once 'bill_util.php';

DoResponse(CgiInput());


function DoResponse($param) {
	echo "Content-Type: text/html\n\n";
	
	if ($param["auth"] == "") {
		throw new ISPErrorException("no auth info");
	} else {
		$info = LocalQuery("payment.recurring.info", array("elid" => $param["elid"]));
    
        $limits = $info->recurring->maxamount;
        if ($limits == "") {
			$limits = "0";
		}
        
		$input = array(
            "response_type" => "code", 
            "scope" => "503", 
            "type" => "rest",
            "redirect_uri" => "https://".$_SERVER["HTTP_HOST"]."/mancgi/paymasterrecurringresult.php?elid=".$param["elid"], 
            "client_id" => $info->payment->paymethod->LMI_MERCHANT_ID."",
            "limits[".$info->payment->currency->iso."]" => $limits.";".$limits.";".$limits
		);

		echo BuildForm(MakePayload($input, $info->payment->paymethod->direct_secret));
	}
}

function MakePayload($param, $secret_key)
{
	$iat = time();
	$sign = base64_encode(hash('sha256', http_build_query($param).';'.$iat.";".$secret_key, true));

	$param["iat"] = $iat;
	$param["sign"] = $sign;

	return $param;
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
		"	<form name='paymasterform' action='https://paymaster.ru/direct/security/auth' method='post'>\n".	
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
