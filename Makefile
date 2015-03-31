all:
	cp -a include /usr/local/mgr5/ && cp -a paymethod/qiwipull/* /usr/local/mgr5/ && killall core