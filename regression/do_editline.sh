#!/bin/sh
#
#   Install editline to various places
#

MAKE=gmake
BASEDIR=$(dirname $PWD)
PLATDIR=$PWD
SRCS=${BASEDIR}/srcs
TARBALLS=${BASEDIR}/tarballs
LIBEDITDIR=${PLATDIR}/install-libedit

if [ ! -e python-editline ]; then
    echo "Extracting python-editline"
    tar xf ${TARBALLS}/python-editline.tar.xz
fi

if [ ! -e python-editline/libedit ]; then
    echo "Installing libedit"
    cd python-editline
    tar xf ${TARBALLS}/libedit-20170329-3.1.tar.gz
    mv libedit-20170329-3.1 libedit
    cd ..
fi

if [ -z "$1" ]; then
    tasks='venv-*-*'
else
    tasks=$1
fi

#for venv in `ls -1d venv-*-*`; do
#for venv in venv-3.6.1-builtin; do
#for venv in venv-3.6.1-dist; do
#for venv in venv-3.6.1-custom; do
for venv in `ls -1d ${tasks}`; do
    
    echo "$venv"

    # start with tidying up
    (cd python-editline; ${MAKE} clean)
    
    # handled the cases
    case ${venv} in
	*-builtin)
	    echo "   builtin libedit"
	    (
		cd python-editline
		${PLATDIR}/${venv}/bin/python3 setup.py \
			  --builtin-libedit install
		cd ..
	    )
	    ;;

	*-custom)
	    echo "   custom libedit"
	    (
		cd python-editline
		export CFLAGS=-I${LIBEDITDIR}/include
		export LDFLAGS=-L${LIBEDITDIR}/lib
		${PLATDIR}/${venv}/bin/python3 setup.py install
		cd ..
	    )
	    ;;

	*-dist)
	    (
		cd python-editline
		${PLATDIR}/${venv}/bin/python3 setup.py install
		cd ..
	    )
	    echo "   distribution libedit"
	    ;;

	*)
	    echo "Unknown configuration"
	    exit
	    ;;
    esac
    
done
