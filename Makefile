all:
	cp -a include /usr/local/mgr5/
	cp -a paymethod/qiwipull/* /usr/local/mgr5/
	cp -a paymethod/paymaster/* /usr/local/mgr5/
	cp -a processing/certificate/globalsign/* /usr/local/mgr5/
	# killall core

globalsign:
	cp -a processing/certificate/globalsign/* /usr/local/mgr5/

cloudpayments:
	@cd paymethod/cloudpayments && sh install.sh