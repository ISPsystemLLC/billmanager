#!/usr/bin/php
<?php

set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "qiwipullpayment");

require_once 'bill_util.php';

echo "Content-Type: text/html\n\n";

$client_ip = ClientIp();
$param = CgiInput();

if ($param["auth"] == "") {
	throw new ISPErrorException("no auth info");
} else {
	$info = LocalQuery("payment.info", array("elid" => $param["elid"], ));
	$elid = (string)$info->payment[0]->id;

	echo "<html>\n";
	echo "<head>\n";
	echo "	<meta http-equiv='Content-Type' content='text/html; charset=UTF-8' />\n";
	echo "	<link rel='shortcut icon' href='billmgr.ico' type='image/x-icon' />\n";
	echo "	<script language='JavaScript'>\n";
	echo "		function DoSubmit() {\n";
	echo "			document.qiwiform.submit();\n";
	echo "		}\n";
	echo "	</script>\n";
	echo "</head>\n";
	echo "<body onload='DoSubmit()'>\n";
	echo "	<form name='qiwiform' action='https://qiwi.com/order/external/main.action' method='post'>\n";
	echo "		<input type='hidden' name='shop' value='" . (string)$info->payment[0]->paymethod[1]->PRV_ID . "'>\n";
	echo "		<input type='hidden' name='transaction' value='" . $elid . "'>\n";
	echo "		<input type='hidden' name='successUrl' value='" . (string)$info->payment[0]->manager_url . "?func=payment.success&elid=" . $elid . "&module=" . __MODULE__ . "'>\n";
	echo "		<input type='hidden' name='failUrl' value='" . (string)$info->payment[0]->manager_url . "?func=payment.fail&elid=" . $elid . "&module=" . __MODULE__ . "'>\n";
	echo "	</form>\n";
	echo "</body>\n";
	echo "</html>\n";
}

?>