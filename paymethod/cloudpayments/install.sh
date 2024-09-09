#!/usr/bin/env sh

. /usr/local/mgr5/lib/pkgsh/core_pkg_funcs.sh

ExitError() {
	Error "${@}"
	exit 1
}

InstallDeps() {
	Info "Install dependencies..."

	PKGS="billmanager-plugin-python-libs"

	case ${OSTYPE} in
		REDHAT)
			PKGS+=" coremanager-devel"
		;;
		DEBIAN)
			PKGS+=" coremanager-dev python3-venv"
		;;
		*)
			ExitError "Unknown os type"
		;;
	esac

	PkgInstall "${PKGS}" || ExitError "Install dependencies failed"
}

InstallCloudPayments() {
	Info "Install CloudPayments..."

	CURRDIR=$(pwd)
	DESTDIR=/usr/local/mgr5/src/cloudpayments

	mkdir -p ${DESTDIR} && cp -rfa "${CURRDIR}"/* ${DESTDIR}/
	cd ${DESTDIR} && make install || ExitError "Install CloudPayments failed"
	cd ${CURRDIR}

	Info "Install successfuly finished"
}

InstallDeps
InstallCloudPayments
