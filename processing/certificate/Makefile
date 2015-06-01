VERSION = 0.0.1
MGR = billmgr
LANGS = en ru

XMLLIST += dist/etc/xml/billmgr_mod_pmthesslstore.xml

WRAPPER += pmthesslstore

pmthesslstore_SOURCES = pmthesslstore.cpp sslutil.cpp util.cpp module.cpp
pmthesslstore_FOLDER = processing
pmthesslstore_LDADD = -lmgr -lmgrdb

SRCDIR=$(BUILD)
BASE ?= ../../../../
include $(BASE)/src/isp.mk
