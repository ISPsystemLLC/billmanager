#!/usr/bin/php
<?php

set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "paymasterresult");

require_once 'bill_util.php';

DoResponse(CgiInput(true));

function DoResponse($param) {
    echo "Content-Type: text/html\n\n";

    $info = LocalQuery("payment.info", array("elid" => $param["elid"]));

    $mydata = $param["LMI_MERCHANT_ID"] + ";" + $param["LMI_PAYMENT_NO"] + ";" + $param["LMI_SYS_PAYMENT_ID"] + ";" + $param["LMI_SYS_PAYMENT_DATE"] + ";" +
              $param["LMI_PAYMENT_AMOUNT"] + ";" + $param["LMI_CURRENCY"] + ";" + $param["LMI_PAID_AMOUNT"] + ";" + $param["LMI_PAID_CURRENCY"] + ";" +
              $param["LMI_PAYMENT_SYSTEM"] + ";" + $param["LMI_SIM_MODE"] + ";" + $info->payment->paymethod->secret;


    if (base64_encode(hash('sha256', $mydata)) == $param["LMI_HASH"])
        SetPaid($param["LMI_SYS_PAYMENT_ID"]);
    else 
        throw new ISPErrorException("invalid hash: ".base64_encode(hash('sha256', $mydata))." != ".$param["LMI_HASH"]);
}

?>