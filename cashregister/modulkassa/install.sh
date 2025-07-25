#!/usr/bin/env sh

. /usr/local/mgr5/lib/pkgsh/core_pkg_funcs.sh

ExitError() {
    Error "${@}"
    exit 1
}

InstallDeps() {
    Info "Install dependencies..."

    PKGS="billmanager-plugin-python-libs billmanager-plugin-paymentreceipt make"

    case ${OSTYPE} in
        REDHAT)
            PKGS="$PKGS coremanager-devel python3-requests"
        ;;
        DEBIAN)
            PKGS="$PKGS coremanager-dev python3-venv python3-pip"
        ;;
        *)
            ExitError "Unknown os type"
        ;;
    esac

    PkgInstall "${PKGS}" || ExitError "Install dependencies failed"
    
    # For Debian/Ubuntu, install python requests via pip
    if [ "${OSTYPE}" = "DEBIAN" ]; then
        Info "Installing Python requests via pip..."
        python3 -m pip install requests || ExitError "Failed to install Python requests"
    fi
}

InstallModulKassa() {
    Info "Install ModulKassa..."

    CURRDIR=$(pwd)
    DESTDIR=/usr/local/mgr5/src/crmodulkassa

    mkdir -p ${DESTDIR} && cp -rfa "${CURRDIR}"/* ${DESTDIR}/
    cd ${DESTDIR} && make install || ExitError "Install ModulKassa failed"
    cd ${CURRDIR}

    Info "Install successfuly finished"
}

InstallDeps
InstallModulKassa