<?php

date_default_timezone_set("UTC");

$log_file = fopen("/usr/local/mgr5/var/". __MODULE__ .".log", "a");
$default_xml_string = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<doc/>\n";

function Debug($str) {
	global $log_file;
	fwrite($log_file, date("M j H:i:s") ." [". getmypid() ."] ". __MODULE__ ." \033[1;33mDEBUG ". $str ."\033[0m\n");
}

function Error($str) {
	global $log_file;
	fwrite($log_file, date("M j H:i:s") ." [". getmypid() ."] ". __MODULE__ ." \033[1;31mERROR ". $str ."\033[0m\n");
}

function tmErrorHandler($errno, $errstr, $errfile, $errline) {
	global $log_file;
	Error("ERROR: ". $errno .": ". $errstr .". In file: ". $errfile .". On line: ". $errline);
	return true;
}

set_error_handler("tmErrorHandler");

function LocalQuery($function, $param, $auth = NULL) {
	$cmd = "/usr/local/mgr5/sbin/mgrctl -m billmgr -o xml " . escapeshellarg($function) . " ";
	foreach ($param as $key => $value) {
		$cmd .= escapeshellarg($key) . "=" . escapeshellarg($value) . " ";
	}

	if (!is_null($auth)) {
		$cmd .= " auth=" . escapeshellarg($auth);
	}

	$out = array();
	exec($cmd, $out);
	$out_str = "";
	foreach ($out as $value) {
		$out_str .= $value . "\n";
	}

	Debug("mgrctl out: ". $out_str);

	return simplexml_load_string($out_str);
}

function HttpQuery($url, $param, $requesttype = "POST", $username = "", $password = "", $header = array("Accept: application/xml")) {
	Debug("HttpQuery url: " . $url);
	Debug("Request: " . http_build_query($param));
	$curl = curl_init($url);
	curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, FALSE);
	curl_setopt($curl, CURLOPT_SSL_VERIFYHOST, FALSE);
	curl_setopt($curl, CURLOPT_RETURNTRANSFER, TRUE);

	if ($requesttype == "DELETE" || $requesttype == "HEAD") {
		curl_setopt($curl, CURLOPT_NOBODY, 1);
	}

	if ($requesttype != "POST" && $requesttype != "GET") {
		curl_setopt($curl, CURLOPT_CUSTOMREQUEST, $requesttype);
	} elseif ($requesttype == "POST") {
		curl_setopt($curl, CURLOPT_POST, 1);
	} elseif ($requesttype == "GET") {
		curl_setopt($curl, CURLOPT_HTTPGET, 1);
	}

	if (count($param) > 0) {
		curl_setopt($curl, CURLOPT_POSTFIELDS, http_build_query($param));
	}

	if (count($header) > 0) {
		curl_setopt($curl, CURLOPT_HTTPHEADER, $header);
	}

	if ($username != "" || $password != "") {
		curl_setopt($curl, CURLOPT_HTTPAUTH, CURLAUTH_BASIC);
		curl_setopt($curl, CURLOPT_USERPWD, $username . ":" . $password);
	}

	$out = curl_exec($curl) or die(curl_error($curl));
	Debug("HttpQuery out: " . $out);
	curl_close($curl);

	return $out;
}

function CgiInput($skip_auth = false) {
	Debug(implode("\n", 
			array_map( function ($v, $k) { return sprintf("%s='%s'", $k, $v); },
			$_SERVER, 
			array_keys($_SERVER))));

	$input = $_SERVER["QUERY_STRING"];
	if ($_SERVER["REQUEST_METHOD"] == 'POST') {
		$size = $_SERVER["CONTENT_LENGTH"];
		if ($size == 0) {
			$size =	$_SERVER["HTTP_CONTENT_LENGTH"];
		}
		if (!feof(STDIN)) {
			$input = $input."&".fread(STDIN, $size);
		}
	}

	$param = array();
	parse_str($input, $param);

	if ($skip_auth == false && (!array_key_exists("auth", $param) || $param["auth"] == "")) {
		if (array_key_exists("billmgrses5", $_COOKIE)) {
			$cookies_bill = $_COOKIE["billmgrses5"];
			$param["auth"] = $cookies_bill;
		} elseif (array_key_exists("HTTP_COOKIE", $_SERVER)) {
			$cookies = explode("; ", $_SERVER["HTTP_COOKIE"]);
			foreach ($cookies as $cookie) {
				$param_line = explode("=", $cookie);
				if (count($param_line) > 1 && $param_line[0] == "billmgrses5") {
					$cookies_bill = explode(":", $param_line[1]);
					$param["auth"] = $cookies_bill[0];
				}
			}
		}

		Debug("auth: " . $param["auth"]);
	}

	if ($skip_auth == false) {
		Debug("auth: " . $param["auth"]);
	}

	return $param;
}

function ClientIp() {
	$client_ip = "";

	if (array_key_exists("HTTP_X_REAL_IP", $_SERVER)) {
		$client_ip = $_SERVER["HTTP_X_REAL_IP"];
	}
	if ($client_ip == "" && array_key_exists("REMOTE_ADDR", $_SERVER)) {
		$client_ip = $_SERVER["REMOTE_ADDR"];
	}

	Debug("client_ip: " . $client_ip);

	return $client_ip;
}

function RandomStr($size = 8) {
    $chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    $chars_size = strlen($chars);
    $result = '';
    for ($i = 0; $i < $size; $i++) {
        $result .= $chars[rand(0, $chars_size - 1)];
    }
    return $result;
}

// Если клиент пожелал сохранить способ оплаты после зачисления платежа
// Вызывать, когда платежная система поддерживает оплату с одновременным сохранением токена
function NeedSaveCardOnPayment($info) {
	return $info->payment->stored_payment == "on";
}

//
//$info - информация о платеже. Помимо этого может содержать сведения для совершения повторных безакцептных платежей, если клиент пожелал сохранить способ оплаты
//$info = array (
// "elid" => 123,  - платеж в биллинге
// "externalid" => "12341423" - платеж на стороне платежки
// "stored_status"      => SavedCardStatuses::rsStored,
// "stored_token"       => "ASDFJKfu89fasdf",
// "stored_name"        => "4xxxxxxxxxxxxx01",
// "stored_expire_date" => "2021-02-02"
//)
function SetPaid($elid, $info) {
	$info["elid"] = $elid;
	LocalQuery("payment.setpaid", $info);
}

function SavePaymethodToken($elid, $info) {
	$info["elid"] = $elid;
	LocalQuery("stored_method.save", $info);
}

function SaveAutopaymentToken($elid, $info) {
	$info["elid"] = $elid;
	LocalQuery("payment.recurring.saveinfo", $info);
}

function AddRedirectAutopaymentSuccessPage() {
	AddRedirectToPage("payment.recurring.success");
}

function AddRedirectAutopaymentFailPage() {
	AddRedirectToPage("payment.recurring.fail");
}

function AddRedirectToStoredMethodSuccessPage() {
	AddRedirectToPage("payment.stored_methods.success");
}

function AddRedirectToStoredMethodFailPage() {
	AddRedirectToPage("payment.stored_methods.fail");
}

function AddRedirectToPage($page) {
	echo "<script language='JavaScript'>location='https://".$_SERVER["HTTP_HOST"]."?func=".$page."'</script>";
}

class ISPErrorException extends Exception
{
	private $m_object = "";
	private $m_value = "";
	private $m_param = "";

	function __construct($message, $object = "", $value = "", $param = array()) {
		parent::__construct($message);
		$this->m_object = $object;
		$this->m_value = $value;
		$this->m_param = $param;
		$error_msg = "Error: ". $message;
		if ($this->m_object != "")
			$error_msg .= ". Object: ". $this->m_object;
		if ($this->m_value != "")
			$error_msg .= ". Value: ". $this->m_value;

		Error($error_msg);
	}

    public function __toString()
    {
    	global $default_xml_string;

        $error_xml = simplexml_load_string($default_xml_string);
        $error_node = $error_xml->addChild("error");
        $error_node->addAttribute("type", parent::getMessage());
        if ($this->m_object != "") {
        	$error_node->addAttribute("object", $this->m_object);
        	$param = $error_node->addChild("param", $this->m_object);
        	$param->addAttribute("name", "object");
        	$param->addAttribute("type", "msg");
        	$param->addAttribute("msg", $this->m_object);
        }
        if ($this->m_value != "") {
        	$param = $error_node->addChild("param", $this->m_value);
        	$param->addAttribute("name", "value");

        	$desc = $error_node->addChild("param", "desck_empty");
        	$desc->addAttribute("name", "desc");
        	$desc->addAttribute("type", "msg");
        }
        foreach ($this->m_param as $name => $value) {
			$param = $error_node->addChild("param", $value);
        	$param->addAttribute("name", $name);
		}
        return $error_xml->asXML();
    }
}

class DB extends mysqli {
	public function __construct($host, $user, $pass, $db) {
		parent::init();
		if (!parent::options(MYSQLI_INIT_COMMAND, "SET AUTOCOMMIT = 1"))
			throw new ISPErrorException("MYSQLI_INIT_COMMAND Fail");

		if (!parent::options(MYSQLI_OPT_CONNECT_TIMEOUT, 5))
			throw new ISPErrorException("MYSQLI_OPT_CONNECT_TIMEOUT Fail");

		if (!parent::real_connect($host, $user, $pass, $db))
			throw new ISPErrorException("Connection ERROR. ".mysqli_connect_errno().": ".mysqli_connect_error());

		Debug("MySQL connection established");
	}

	public function __destruct() {
		parent::close();
		Debug("MySQL connection closed");
	}
}

?>
