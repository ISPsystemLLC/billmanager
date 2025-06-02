XML_DIR = /usr/local/mgr5/etc/xml/
EXEC_DIR = /usr/local/mgr5/processing/
LOGO_DIR = /usr/local/mgr5/skins/common/plugin-logo

.ONESHELL:

all: install

install:
	# requirements
	python3 -m venv pter-venv
	. $(CURDIR)/pter-venv/bin/activate
	pip3 install -r $(CURDIR)/requirements.txt
	#bash gen script for running module
	echo '#!/bin/bash\n . ${CURDIR}/pter-venv/bin/activate\n python ${CURDIR}/pmpterodactyl.py "$$@"' > $(CURDIR)/pmpterodactyl
	# logo
	cp ./assets/billmanager-plugin-pmpterodactyl.png  $(LOGO_DIR)
	# xml
	cp ./billmgr_mod_pmpterodactyl.xml $(XML_DIR)
	# main exec
	ln -snf $(shell pwd)/pmpterodactyl $(EXEC_DIR)pmpterodactyl
	chmod 775 $(EXEC_DIR)pmpterodactyl
	# restart billmgr
	/usr/local/mgr5/sbin/mgrctl -m billmgr -R
