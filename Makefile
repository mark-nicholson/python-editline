#
#  Maintenance tool
#

PYTHON?=/usr/bin/python3
PYTHON_VERSION=$(shell $(PYTHON) -c "import sys; print(sys.version[:5])")
PYTHON_VER=$(shell $(PYTHON) -c "import sys; print(sys.version[:3])")
PYTHON_PLAT=$(shell $(PYTHON) -c "import sys; print(sys.platform)")
MACHINE=$(shell uname -m)
PY_BUILD_LIB_DIR=build/lib.$(PYTHON_PLAT)-$(MACHINE)-$(PYTHON_VER)

TMP_LIBEDIT=/tmp/libedit
CFG_LIBEDIT=$(TMP_LIBEDIT)-cfg
SRC_LIBEDIT=src/libedit


all: src/libedit
	@echo "Done"

src/libedit:
	@rm -rf $(TMP_LIBEDIT) $(CFG_LIBEDIT)
	@rm -rf $(SRC_LIBEDIT)
	git clone git@github.com:mark-nicholson/libedit.git $(TMP_LIBEDIT)
	sed -i'' 's/0:56:1/0:57:0/' $(TMP_LIBEDIT)/configure.ac $(TMP_LIBEDIT)/ChangeLog
	cd $(TMP_LIBEDIT) && $(TMP_LIBEDIT)/autogen
	mkdir $(CFG_LIBEDIT)
	cd $(CFG_LIBEDIT) && $(TMP_LIBEDIT)/configure
	mkdir -p $(SRC_LIBEDIT)/gen
	cp $(TMP_LIBEDIT)/config.h.in $(SRC_LIBEDIT)
	cp -R $(TMP_LIBEDIT)/src $(SRC_LIBEDIT)
	rm $(SRC_LIBEDIT)/src/Make*
	$(MAKE) -C $(CFG_LIBEDIT)
	cp $(CFG_LIBEDIT)/src/*.h $(SRC_LIBEDIT)/gen

src/check/configure:
	$(MAKE) -C src/check

clean:
	@rm -rf build __pycache__
	@rm -f *~ MANIFEST
	$(MAKE) -C docs clean

distclean: clean
	@rm -rf venv dist hostconf /tmp/hctmp
	$(MAKE) -C docs distclean

venv:
	@rm -rf venv
	$(PYTHON) -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install twine
	venv/bin/pip install Sphinx
	venv/bin/pip install pylint

/tmp/hctmp:
	@rm -rf /tmp/hctmp
	git clone git@github.com:mark-nicholson/python-hostconf.git /tmp/hctmp

hostconf: /tmp/hctmp
	rm -rf hostconf
	cp -r /tmp/hctmp/hostconf .
	rm -rf hostconf/test*

dist: venv hostconf
	venv/bin/python3 setup.py sdist

clean-venv:
	@find venv/lib/python3.5/site-packages/ -name '*edit*' | xargs /bin/rm -rf
	@rm venv/lib/python3.5/site-packages/sitecustomize.py*

upload: dist
	venv/bin/twine upload dist/pyeditline*.tar.gz

test-upload: dist
	venv/bin/twine upload --repository-url https://test.pypi.org/legacy/ dist/pyeditline*.tar.gz

#
#  PIP install from test-site:
#
#    pip install --index-url https://test.pypi.org/simple/ pyeditline
#

#
#  TestBed
#

TESTBED_EDITLINE=testbed/venv/lib/python$(PYTHON_VER)/site-packages/editline
TESTBED_RELPATH=../../../../../../editline

testbed-clean: clean
	@rm -rf testbed

testbed:
	mkdir testbed

testbed/venv: testbed
	$(PYTHON) -m venv testbed/venv
	testbed/venv/bin/pip install --upgrade pip
	testbed/venv/bin/pip install nose
	testbed/venv/bin/python3 setup.py install

testbed/links:
	@rm -rf $(TESTBED_EDITLINE)/editline.py
	@ln -s $(TESTBED_RELPATH)/editline.py $(TESTBED_EDITLINE)/editline.py
	@rm -rf $(TESTBED_EDITLINE)/lineeditor.py
	@ln -s $(TESTBED_RELPATH)/lineeditor.py $(TESTBED_EDITLINE)/lineeditor.py
	@rm -rf $(TESTBED_EDITLINE)/tests
	@ln -s $(TESTBED_RELPATH)/tests $(TESTBED_EDITLINE)/tests

test: testbed/venv testbed/links
	cd testbed && venv/bin/python3 -m unittest discover -v -s ../$(TESTBED_EDITLINE)


vars:
	@echo "Python Version:  " $(PYTHON_VERSION)
	@echo "Python Ver:      " $(PYTHON_VER)
	@echo "Dir:             " $(PY_BUILD_LIB_DIR)
