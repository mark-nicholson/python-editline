#!/bin/sh

#LIBEDIT_SRC=/work/mjn/libedit/python-editline
LIBEDIT_SRC=/work/mjn/python/solaris/python-editline
LIBPATH=lib/python3.?/site-packages

# repair
for venv in `ls -1d venv-*-*`; do
    cp ${LIBEDIT_SRC}/test/test_editline.py  ${venv}/${LIBPATH}/test/
    cp ${LIBEDIT_SRC}/test/test_lineeditor.py  ${venv}/${LIBPATH}/test/
    cp ${LIBEDIT_SRC}/test/expty.py  ${venv}/${LIBPATH}/test/
done

# prep the site-override
for venv in `ls -1d venv-*-*`; do
    cp ${LIBEDIT_SRC}/siteconfig/sitecustomize.py  ${venv}/${LIBPATH}/
done
