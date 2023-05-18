#include "sslutil.h"

MODULE ("sslutil");

namespace ssl_util {
	Template::Template(mgr_xml::XmlNode tmpl_node)
	: is_wildcard	(false)
	, is_www		(false)
	, is_multidomain(false)
	, is_idn		(false)
	, is_orginfo	(false)
	, is_codesign	(false)
	, is_csraltname		(false) {
		name			= tmpl_node.GetProp("name");
		is_wildcard		= tmpl_node.GetProp(TEMPLATE_WILDCARD) == "yes";
		is_www			= tmpl_node.GetProp(TEMPLATE_WWW) == "yes";
		is_multidomain	= tmpl_node.GetProp(TEMPLATE_MULTIDOMAIN) == "yes";
		is_idn			= tmpl_node.GetProp(TEMPLATE_IDN) == "yes";
		is_orginfo		= tmpl_node.GetProp(TEMPLATE_ORGINFO) == "yes";
		is_codesign		= tmpl_node.GetProp(TEMPLATE_CODESIGN) == "yes";
		is_csraltname			= tmpl_node.GetProp(TEMPLATE_CSRALTNAME) == "yes";
	}

void Template::AsXml(mgr_xml::Xml &xml) {
	STrace();
	auto node = xml.GetRoot().AppendChild("template");
	node.AppendChild("name", name);
	node.AppendChild(TEMPLATE_WILDCARD, is_wildcard ? "yes" : "no");
	node.AppendChild(TEMPLATE_WWW, is_www ? "yes" : "no");
	node.AppendChild(TEMPLATE_MULTIDOMAIN, is_multidomain ? "yes" : "no");
	node.AppendChild(TEMPLATE_IDN, is_idn ? "yes" : "no");
	node.AppendChild(TEMPLATE_ORGINFO, is_orginfo ? "yes" : "no");
	node.AppendChild(TEMPLATE_CODESIGN, is_codesign ? "yes" : "no");
	node.AppendChild(TEMPLATE_CSRALTNAME, is_csraltname ? "yes" : "no");
	Debug("result node = '%s'", node.Str().c_str());
	Debug("result xml = '%s'", xml.Str().c_str());
}

Template::TemplateMap &Template::Get() {
	static TemplateMap map;
	return map;
}

void Template::Insert(const string &module, mgr_xml::XmlNode config) {
	Get()[module].push_back(Template(config));
}

void Template::AsXml(const std::string &module, mgr_xml::Xml& xml) {
	STrace();
	ForEachI(Template::Get()[module], t) {
		t->AsXml(xml);
	}
}

int OrderedAltNamesCount(std::shared_ptr<mgr_db::Cache> db, int iid) {
	return str::Int(db->Query(
						"SELECT SUM(IF(ap.addontype = " + str::Str(table::atInteger) + ", IFNULL(a.addonlimit, ap.addonlimit) + IFNULL(a.intvalue, 0), CONVERT(ei.intname, UNSIGNED))) "
						"FROM item i "
						"JOIN pricelist p ON p.id = i.pricelist "
						"LEFT JOIN pricelist ap ON ap.parent = p.id "
						"JOIN item a ON a.parent = i.id AND a.pricelist = ap.id "
						"JOIN itemtype it ON it.id = ap.itemtype "
						"LEFT JOIN enumerationitem ei ON ei.id = a.enumerationitem "
	                    "WHERE i.id = " + str::Str(iid) + " AND it.intname = " + db->EscapeValue(CERTIFICATE_ALTNAME))->Str());
}

}