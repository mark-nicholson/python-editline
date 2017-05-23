#!/bin/bash

LIBEDIT_SRC=/work/mjn/libedit/python-editline
LIBPATH=lib/python3.?/site-packages
PLATDIR=${PWD}

#for venv in `ls -1d venv-*-*`; do
for venv in `ls -1d venv-3.6.1-*`; do
    echo "Testing ${venv}"
    rm -f ${venv}-check.log
    touch ${venv}-check.log
    date >> ${venv}-check.log

    case ${venv} in
	*-custom)
	    link_env=LD_LIBRARY_PATH=${PLATDIR}/install-libedit/lib
	    echo "   test_editline"
	    (
		export ${link_env}
		${venv}/bin/python3 ${venv}/${LIBPATH}/test/test_editline.py -v >> ${venv}-check.log 2>&1
	    )
    
	    echo "   test_lineeditor"
	    (
		export ${link_env}
		${venv}/bin/python3 ${venv}/${LIBPATH}/test/test_lineeditor.py -v >> ${venv}-check.log 2>&1
	    )
	    ;;

	*-dist|*-builtin)
	    echo "   test_editline"
	    ${venv}/bin/python3 ${venv}/${LIBPATH}/test/test_editline.py -v >> ${venv}-check.log 2>&1
    
	    echo "   test_lineeditor"
	    ${venv}/bin/python3 ${venv}/${LIBPATH}/test/test_lineeditor.py -v >> ${venv}-check.log 2>&1
	    ;;

	*)
	    echo "   INVALID venv"
	    ;;

    esac

done
