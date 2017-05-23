#!/bin/sh

LIBEDIT_SRC=/work/mjn/libedit/python-editline
LIBPATH=lib/python3.?/site-packages
PLATDIR=${PWD}

if [ -z "$1" ]; then
    tasks='venv-*-*'
else
    tasks=$1
fi

#for venv in `ls -1d venv-*-*`; do
#for venv in `ls -1d venv-3.7.0a-*`; do
#for venv in `ls -1d venv-3.6.1-*`; do
#for venv in `ls -1d venv-3.5.3-*`; do
#for venv in `ls -1d venv-3.4.6-*`; do
for venv in `ls -1d ${tasks}`; do
    echo "Testing ${venv}"

    case ${venv} in
	*-custom)
	    link_env=LD_LIBRARY_PATH=${PLATDIR}/install-libedit/lib
	    echo "   test_editline"
	    (
		export ${link_env}
		${venv}/bin/python3 ${venv}/${LIBPATH}/test/test_editline.py
	    )
    
	    echo "   test_lineeditor"
	    (
		export ${link_env}
		${venv}/bin/python3 ${venv}/${LIBPATH}/test/test_lineeditor.py
	    )
	    ;;

	*-dist|*-builtin)
	    echo "   test_editline"
	    ${venv}/bin/python3 ${venv}/${LIBPATH}/test/test_editline.py
    
	    echo "   test_lineeditor"
	    ${venv}/bin/python3 ${venv}/${LIBPATH}/test/test_lineeditor.py
	    ;;

	*)
	    echo "   INVALID venv"
	    ;;

    esac

done
