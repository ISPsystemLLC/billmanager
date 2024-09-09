XML_DIR = /usr/local/mgr5/etc/xml/
EXEC_DIR = /usr/local/mgr5/processing/
LOGO_DIR = /usr/local/mgr5/skins/common/plugin-logo

all: install

install:
	apt install python3-pip
	apt install billmanager-plugin-python-libs
	pip install -r requirements.txt
	#xml
	cp ./billmgr_mod_pmpterodactyl.xml  $(XML_DIR)
	#main exec
	ln -snf $(shell pwd)/pmpterodactyl.py $(EXEC_DIR)pmpterodactyl
	chmod 775 $(EXEC_DIR)pmpterodactyl
	cp ./assets/billmanager-plugin-pmpterodactyl.png  $(LOGO_DIR)
	/usr/local/mgr5/sbin/mgrctl -m billmgr -R
