<?php

$log_file = fopen("/usr/local/mgr5/var/". __MODULE__ .".log", "a");
$default_xml_string = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<doc/>\n";

function tmErrorHandler($errno, $errstr, $errfile, $errline) {
	global $log_file;
	fwrite($log_file, date("M j H:i:s") ." [". getmypid() ."] ERROR: ". $errno .": ". $errstr .". In file: ". $errfile .". On line: ". $errline ."\n");
	return true;
}

set_error_handler("tmErrorHandler");

function Debug($str) {
	global $log_file;
	fwrite($log_file, date("M j H:i:s") ." [". getmypid() ."] ". __MODULE__ ." \033[1;33mDEBUG ". $str ."\033[0m\n");
}

function Error($str) {
	global $log_file;
	fwrite($log_file, date("M j H:i:s") ." [". getmypid() ."] ". __MODULE__ ." \033[1;31mERROR ". $str ."\033[0m\n");
}

class Error extends Exception
{
	function __construct($message = "", $code = 0, $previous = NULL) {
		parent::__construct($message, $code, $previous);
		Error("Error: ". $message);
	}

    public function __toString()
    {
        $error_xml = simplexml_load_string($default_xml_string);
        $error_node = $error_xml->addChild("error");
        $error_node->addAttribute("type", parent::getMessage());
        return $error_xml->asXML();
    }
}
?>