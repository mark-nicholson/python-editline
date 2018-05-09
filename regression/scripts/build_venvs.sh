#!/bin/sh
#
#   Cook up the virtual-envs
#

SCRIPTS_DIR="$(dirname $0)"
REGR_DIR="$(dirname ${SCRIPTS_DIR})"
SRCS_DIR="${REGR_DIR}/srcs"
BASE_DIR="../${REGR_DIR}"


if [ -z "${VER}" ]; then
    echo "Must define VER="
    exit 1
fi

echo "Version: ${VER}"

if [ "${VER}" = "all" ]; then
    versions="3.7.0b2 3.6.4 3.5.5 3.4.7 3.3.7"
else
    versions=${VER}
fi

for ver in ${versions}; do

    echo "VENVs for ${ver}"

    for cfg in dist builtin custom pip; do

	# build the venv
	install-${ver}/bin/python3 -m venv venv-${ver}-${cfg}

	if [ "${ver}" = "3.3.7" ]; then
	    venv-${ver}-${cfg}/bin/python3 ${SRCS_DIR}/get-pip.py
	fi

	# install some basics 
	venv-${ver}-${cfg}/bin/pip install --upgrade pip

    done

done
