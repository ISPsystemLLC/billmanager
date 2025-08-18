#!/usr/bin/env bash

. /usr/local/mgr5/lib/pkgsh/core_pkg_funcs.sh

ExitError() {
	Error "${@}"
	exit 1
}

InstallDeps() {
	Info "Installing dependencies..."

	PKGS="billmanager-plugin-python-libs python3-pip make"

	case ${OSTYPE} in
		REDHAT)
			PKGS="$PKGS coremanager-devel"
		;;
		DEBIAN)
			PKGS="$PKGS coremanager-dev python3-venv"
		;;
		*)
			ExitError "Unknown os type"
		;;
	esac

	PkgInstall "${PKGS}" || ExitError "Failed to install system packages"
	python3 -m venv venv-nextcloud || ExitError "Failed to create venv"
	VENV_DIR="./venv-nextcloud"

	"$VENV_DIR/bin/pip3" install --upgrade pip || ExitError "pip upgrade failed"
	"$VENV_DIR/bin/pip3" install -r ./requirements.txt || ExitError "Failed to install Python dependencies"
}

InstallNextcloud() {
	Info "Install Nextcloud..."

	CURRDIR=$(pwd)
	DESTDIR=/usr/local/mgr5/src/pmnextcloud

	mkdir -p ${DESTDIR} && cp -rfa "${CURRDIR}"/* ${DESTDIR}/
	cd ${DESTDIR} && make install || ExitError "Install Nextcloud failed"
	cd ${CURRDIR}

	Info "Install successfuly finished"
}

InstallDeps
InstallNextcloud
