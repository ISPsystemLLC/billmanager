#!/usr/bin/env sh

. /usr/local/mgr5/lib/pkgsh/core_pkg_funcs.sh

ExitError() {
	Error "${@}"
	exit 1
}

InstallDeps() {
	PKGS="billmanager-plugin-python-libs python3-pip make"
	Info "Install dependencies: ${PKGS}"
	PkgInstall "${PKGS}" || ExitError "Install dependencies failed"
}

InstallBillPterodactyl() {
	Info "Install BillPterodactyl..."
	make install || ExitError "Install BillPterodactyl failed"
	Info "Install successfuly finished"
}

InstallDeps
InstallBillPterodactyl
