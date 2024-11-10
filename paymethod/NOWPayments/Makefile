MGR = billmgr
PLUGIN = pmnowpayments

NOWPAYMENTS_SRC=$(shell pwd)

dist-prepare: $(DISTDIR)/paymethods/pmnowpayments
$(DISTDIR)/paymethods/pmnowpayments: $(NOWPAYMENTS_SRC)/pmnowpayments.py
	@echo "NOWPayments: Copy nowpayments module"
	@mkdir -p $(DISTDIR)/paymethods && \
		cp -f $(NOWPAYMENTS_SRC)/pmnowpayments.py $(DISTDIR)/paymethods/pmnowpayments && \
		chmod 744 $(DISTDIR)/paymethods/pmnowpayments

dist-prepare: $(DISTDIR)/cgi/nowpaymentspayment
$(DISTDIR)/cgi/nowpaymentspayment: $(NOWPAYMENTS_SRC)/nowpaymentspayment.py
	@echo "NOWPayments: Copy nowpaymentspayment cgi"
	@mkdir -p $(DISTDIR)/cgi && \
		cp -f $(NOWPAYMENTS_SRC)/nowpaymentspayment.py $(DISTDIR)/cgi/nowpaymentspayment && \
		chmod 744 $(DISTDIR)/cgi/nowpaymentspayment

dist-prepare: $(DISTDIR)/cgi/nowpaymentsresult
$(DISTDIR)/cgi/nowpaymentsresult: $(NOWPAYMENTS_SRC)/nowpaymentsresult.py
	@echo "NOWPayments: Copy nowpaymentsresult"
	@mkdir -p $(DISTDIR)/cgi && \
		cp -f $(NOWPAYMENTS_SRC)/nowpaymentsresult.py $(DISTDIR)/cgi/nowpaymentsresult && \
		chmod 744 $(DISTDIR)/cgi/nowpaymentsresult

dist-prepare: $(DISTDIR)/lib/python/nowpayments
$(DISTDIR)/lib/python/nowpayments: $(NOWPAYMENTS_SRC)/nowpayments/*
	@echo "NOWPayments: Copy nowpayments api, etc."
	@mkdir -p $(DISTDIR)/lib/python/nowpayments && \
		cp -f $(NOWPAYMENTS_SRC)/nowpayments/* $(DISTDIR)/lib/python/nowpayments/

dist-prepare: $(DISTDIR)/etc/xml/billmgr_mod_pmnowpayments.xml
$(DISTDIR)/etc/xml/billmgr_mod_pmnowpayments.xml: $(NOWPAYMENTS_SRC)/xml/billmgr_mod_pmnowpayments.xml
	@echo "NOWPayments: Copy nowpayments xml"
	@mkdir -p $(DISTDIR)/etc/xml && \
		cp -f $(NOWPAYMENTS_SRC)/xml/billmgr_mod_pmnowpayments.xml $(DISTDIR)/etc/xml/

dist-prepare: $(DISTDIR)/skins/common/plugin-logo/billmanager-plugin-pmnowpayments.png
$(DISTDIR)/skins/common/plugin-logo/billmanager-plugin-pmnowpayments.png: $(NOWPAYMENTS_SRC)/dist/skins/common/plugin-logo/billmanager-plugin-pmnowpayments.png
	@echo "NOWPayments: Copy nowpayments logo"
	@mkdir -p $(DISTDIR)/skins/common/plugin-logo && \
		cp -f $(NOWPAYMENTS_SRC)/dist/skins/common/plugin-logo/billmanager-plugin-pmnowpayments.png $(DISTDIR)/skins/common/plugin-logo/

BASE ?= /usr/local/mgr5
include $(BASE)/src/isp.mk