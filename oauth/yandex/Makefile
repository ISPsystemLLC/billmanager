MGR=billmgr
PLUGIN=omyandex

dist-prepare:
	@mkdir -p $(DISTDIR)/oauth && cp -f oauth/omyandex.py $(DISTDIR)/oauth/omyandex && chmod 744 $(DISTDIR)/oauth/omyandex

BASE ?= /usr/local/mgr5
include $(BASE)/src/isp.mk