all:
	cp -a include /usr/local/mgr5/
	cp -a paymethod/qiwipull/* /usr/local/mgr5/
	cp -a paymethod/paymaster/* /usr/local/mgr5/
	cp -a processing/registrar/* /usr/local/mgr5/
	# killall core