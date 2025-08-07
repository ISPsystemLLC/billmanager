#include <mgr/mgrlog.h>

#include <bill/project.h>

MODULE("yandex");

namespace {

class YandexMethod : public project::MethodOAuth {
public:
	YandexMethod() : MethodOAuth("yandex") {}

	string GetUserLink(const string& /*user_id*/) const final {
		return "https://id.yandex.ru";
	}
};

} // namespace

MODULE_INIT(yandex, "billmgr") {
	project::Register<YandexMethod>();
}