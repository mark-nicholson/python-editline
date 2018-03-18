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

# reference the common repo here
if [ ! -e python-editline ]; then
    ln -s ../.. python-editline
fi

# select all venvs or else use the provided argument
if [ -z "$1" ]; then
    tasks='venv-*-*-'
else
    tasks=$1
fi

# prepare each of the virtual-envs
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
			  build_ext --builtin-libedit install
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