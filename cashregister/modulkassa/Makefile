MGR = billmgr
PLUGIN = crmodulkassa

MODULKASSA_SRC=$(shell pwd)

dist-prepare: $(DISTDIR)/cashregister/crmodulkassa
$(DISTDIR)/cashregister/crmodulkassa: $(MODULKASSA_SRC)/crmodulkassa.py
	@echo "ModulKassa: Copy crmodulkassa module"
	@mkdir -p $(DISTDIR)/cashregister && \
		cp -f $(MODULKASSA_SRC)/crmodulkassa.py $(DISTDIR)/cashregister/crmodulkassa && \
		chmod 744 $(DISTDIR)/cashregister/crmodulkassa

dist-prepare: $(DISTDIR)/lib/python/modulkassa
$(DISTDIR)/lib/python/modulkassa: $(MODULKASSA_SRC)/modulkassa/*
	@echo "ModulKassa: Copy modulkassa api"
	@mkdir -p $(DISTDIR)/lib/python/modulkassa && \
		cp -f $(MODULKASSA_SRC)/modulkassa/* $(DISTDIR)/lib/python/modulkassa/

BASE ?= /usr/local/mgr5
include $(BASE)/src/isp.mk