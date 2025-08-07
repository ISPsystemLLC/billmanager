MGR=billmgr
PLUGIN=oauth_yandex

CFLAGS += -I/usr/local/mgr5/include/billmgr
CXXFLAGS += -I/usr/local/mgr5/include/billmgr

LIB += libyoauthyandex
libyoauthyandex_LDADD = -lmgrdb -lispapi
libyoauthyandex_SOURCES = src/oauth_yandex.cpp

dist-prepare:
	@mkdir -p $(DISTDIR)/oauth && cp -f oauth/omyandex.py $(DISTDIR)/oauth/omyandex && chmod 744 $(DISTDIR)/oauth/omyandex

BASE ?= /usr/local/mgr5
include $(BASE)/src/isp.mk