#!/usr/bin/php
<?php

set_include_path(get_include_path() . PATH_SEPARATOR . "/usr/local/mgr5/include/php");
define('__MODULE__', "paymasterrecurringresult");

require_once 'bill_util.php';

//старые механизм - автоплатежи
class AutopaymentStatuses
{
    const rsAdd		= '0';  // в процессе настройки
    const rsActive	= '1';  // активно
    const rsClosed	= '2';  // отключено

    public static function IsAutoPayment($status) {
        return $status == self::rsAdd || $status == self::rsActive || $status == self::rsClosed; 
    } 
}

//новый механизм - сохраненные способы оплаты
class SavedCardStatuses
{
    const rsStoring	    = '3';  // в процессе настройки, чтобы не ломать старую логику с rsAdd
    const rsStored	    = '4';  // работоспособный сохраненный способ оплаты, чтобы не ломать старую логику с rsActive
    const rsDisabled	= '5';  // отключенный сохраненный способ оплаты
    const rsRestoring	= '6';  // перенастройка сохранённого способа оплаты
    const rsError		= '10'; // ошибка
}

DoResponse(CgiInput(true));

function DoResponse($param) {
    echo "Content-Type: text/html\n\n";

    $info = LocalQuery("payment.recurring.info", array("elid" => $param["elid"]));
    $out_json = GetCardTokenResponse($param, $info);

    $is_autopayment = AutopaymentStatuses::IsAutoPayment($info->recurring->status);
    $is_savedcard = !$is_autopayment;

    if (ErrorExists($out_json)) {
        if ($is_savedcard)
            AddRedirectToStoredMethodFailPage();
        else
            AddRedirectAutopaymentFailPage();
    } else {
        if ($is_savedcard) {
            $date = new DateTime();
            $date->add(new DateInterval('PT'.$out_json->expires_in.'S'));

            $card_info = array (
                "stored_status"      => SavedCardStatuses::rsStored,
                "stored_token"       => $out_json->access_token,
                "stored_name"        => $out_json->account_identifier,
                "stored_expire_date" => $date->format('Y-m-d')
            );
            SavePaymethodToken($param["elid"], $card_info);

            AddRedirectToStoredMethodSuccessPage();
        } else {
            $autopayment_info = array (
                "status"    => AutopaymentStatuses::rsActive,
                "token"     => $out_json->access_token,
                "data1"     => $out_json->account_identifier,
                "data2"     => $out_json->account_identifier
            );

            SaveAutopaymentToken($param["elid"], $autopayment_info);

            AddRedirectAutopaymentSuccessPage();
        }
    }
}

function ErrorExists($out_json) {
    return property_exists($out_json, "error");
}

function GetCardTokenResponse($param, $info) {
    $payload = array( 
        "code" => $param["code"],
        "client_id" => $info->payment->paymethod->LMI_MERCHANT_ID."",
        "grant_type" => "authorization_code",
        "redirect_uri" => "https://".$_SERVER["HTTP_HOST"]."/mancgi/paymasterrecurringresult.php?elid=".$param["elid"],
        "type" => "rest"
    );

    $out = HttpQuery("https://paymaster.ru/direct/security/token",
                     MakePayload($payload, $info->payment->paymethod->direct_secret),
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