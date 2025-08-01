MGR = billmgr
PLUGIN = pmnextcloud

SRC=$(shell pwd)

dist-prepare: $(DISTDIR)/processing/pmnextcloud
$(DISTDIR)/processing/pmnextcloud: $(SRC)/src/pmnextcloud.py
	@echo "Nextcloud: Copy pmnextcloud module"
	@mkdir -p $(DISTDIR)/processing && \
		ln -snf $(SRC)/src/pmnextcloud.py $(DISTDIR)/processing/pmnextcloud && \
		chmod 755 $(DISTDIR)/processing/pmnextcloud


BASE ?= /usr/local/mgr5
include $(BASE)/src/isp.mk