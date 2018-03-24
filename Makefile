#
#  Maintenance tool
#

PYTHON?=/work/mjn/python/python-editline/regression/ubuntu-16.04.4/install-3.6.4/bin/python3

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

md-to-rst:
	pandoc --from=markdown --to=rst --output README.rst README.md

clean:
	@rm -rf build __pycache__
	@rm -f *~ README.rst MANIFEST

distclean: clean
	@rm -rf venv dist

venv:
	@rm -rf venv
	$(PYTHON) -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install twine

dist: venv md-to-rst
	venv/bin/python3 setup.py sdist

clean-venv:
	@find venv/lib/python3.5/site-packages/ -name '*edit*' | xargs /bin/rm -rf
	@rm venv/lib/python3.5/site-packages/sitecustomize.py*



update-libedit:
