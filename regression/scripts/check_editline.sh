#!/bin/sh

#LIBPATH=lib/python3.?/site-packages
LIBPATH=../..
PLATDIR=${PWD}

TEST_PATH=${LIBPATH}/editline/tests
TEST_FILES="test_editline.py test_lineeditor.py test_list_completion.py test_dict_completion.py"

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
	    (
		export ${link_env}
		for tf in ${TEST_FILES}; do
		    echo "*** $tf"
		    ${venv}/bin/python3 ${TEST_PATH}/${tf}
		done
	    )
	    echo "done"
	    ;;

	*-dist|*-builtin|*-pip)
	    for tf in ${TEST_FILES}; do
		echo "*** $tf"
		${venv}/bin/python3 ${TEST_PATH}/${tf}
	    done
	    ;;

	*)
	    echo "   INVALID venv"
	    ;;

    esac

done
