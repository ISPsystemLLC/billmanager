MGR = billmgr
PLUGIN = pmcloudpaymentswidget

CP_SRC=$(shell pwd)

dist-prepare: $(DISTDIR)/paymethods/pmcloudpaymentswidget
$(DISTDIR)/paymethods/pmcloudpaymentswidget: $(CP_SRC)/pmcloudpaymentswidget.py
	@echo 'CloudPayments: Copy pmcloudpaymentswidget module'
	@mkdir -p $(DISTDIR)/paymethods && \
		cp -f $(CP_SRC)/pmcloudpaymentswidget.py $(DISTDIR)/paymethods/pmcloudpaymentswidget && \
		chmod 744 $(DISTDIR)/paymethods/pmcloudpaymentswidget

dist-prepare: $(DISTDIR)/cgi/cpwidgetpayment
$(DISTDIR)/cgi/cpwidgetpayment: $(CP_SRC)/cpwidgetpayment.py
	@echo 'CloudPayments: Copy cpwidgetpayment cgi'
	@mkdir -p $(DISTDIR)/cgi && \
		cp -f $(CP_SRC)/cpwidgetpayment.py $(DISTDIR)/cgi/cpwidgetpayment && \
		chmod 744 $(DISTDIR)/cgi/cpwidgetpayment

dist-prepare: $(DISTDIR)/cgi/cpwidgetresult
$(DISTDIR)/cgi/cpwidgetresult: $(CP_SRC)/cpwidgetresult.py
	@echo 'CloudPayments: Copy cpwidgetresult cgi'
	@mkdir -p $(DISTDIR)/cgi && \
		cp -f $(CP_SRC)/cpwidgetresult.py $(DISTDIR)/cgi/cpwidgetresult && \
		chmod 744 $(DISTDIR)/cgi/cpwidgetresult

dist-prepare: $(DISTDIR)/cgi/cpwidgetrecurring
$(DISTDIR)/cgi/cpwidgetrecurring: $(CP_SRC)/cpwidgetrecurring.py
	@echo 'CloudPayments: Copy cpwidgetrecurring cgi'
	@mkdir -p $(DISTDIR)/cgi && \
		cp -f $(CP_SRC)/cpwidgetrecurring.py $(DISTDIR)/cgi/cpwidgetrecurring && \
		chmod 744 $(DISTDIR)/cgi/cpwidgetrecurring

dist-prepare: $(DISTDIR)/cgi/cpwidgetrecurringresult
$(DISTDIR)/cgi/cpwidgetrecurringresult: $(CP_SRC)/cpwidgetrecurringresult.py
	@echo 'CloudPayments: Copy cpwidgetrecurringresult cgi'
	@mkdir -p $(DISTDIR)/cgi && \
		cp -f $(CP_SRC)/cpwidgetrecurringresult.py $(DISTDIR)/cgi/cpwidgetrecurringresult && \
		chmod 744 $(DISTDIR)/cgi/cpwidgetrecurringresult

dist-prepare: $(DISTDIR)/lib/python/cloudpayments
$(DISTDIR)/lib/python/cloudpayments: $(CP_SRC)/cloudpayments/*
	@echo 'CloudPayments: Copy cloudpayments api'
	@mkdir -p $(DISTDIR)/lib/python/cloudpayments && \
		cp -f $(CP_SRC)/cloudpayments/* $(DISTDIR)/lib/python/cloudpayments/

BASE ?= /usr/local/mgr5
include $(BASE)/src/isp.mk