#!/bin/sh

#LIBPATH=lib/python3.?/site-packages
LIBPATH=../../..
PLATDIR=${PWD}
TEST_EDITLINE=${LIBPATH}/test/test_editline.py
TEST_LINEEDITOR=${LIBPATH}/test/test_lineeditor.py

if [ -z "$1" ]; then
    tasks='venv-*-*'
else
    tasks=$1
fi

# iterate over the selected virtual-envs
for venv in `ls -1d ${tasks}`; do
    echo "Testing ${venv}"

    logfile=${venv}/results.log

    case ${venv} in
	*-custom)
	    link_env=LD_LIBRARY_PATH=${PLATDIR}/install-libedit/lib
	    echo -n "*** test_editline ... "
	    (
		export ${link_env}
		${venv}/bin/python3 ${venv}/${TEST_EDITLINE}
	    )
	    echo "done"
    
	    echo -n "*** test_lineeditor"
	    (
		export ${link_env}
		${venv}/bin/python3 ${venv}/${TEST_LINEEDITOR}
	    )
	    echo "done"
	    ;;

	*-dist|*-builtin)
	    echo "*** test_editline"
	    ${venv}/bin/python3 ${venv}/${TEST_EDITLINE}
    
	    echo "*** test_lineeditor"
	    ${venv}/bin/python3 ${venv}/${TEST_LINEEDITOR}
	    ;;

	*)
	    echo "   INVALID venv"
	    ;;

    esac

done
