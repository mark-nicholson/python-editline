#
#  Maintenance tool
#

PYTHON?=python3

all: libedit check/configure
	@echo "Done"

libedit:
	git clone git@github.com:mark-nicholson/libedit.git --branch release --single-branch libedit

check/configure:
	$(MAKE) -C check

md-to-rst:
	pandoc --from=markdown --to=rst --output README.rst README.md

clean:
	@$(MAKE) -C check clean
	@rm -rf build __pycache__
	@rm -f *~ README.rst MANIFEST

distclean: clean
	@$(MAKE) -C check distclean
	@rm -rf libedit
	@rm -rf venv dist

venv:
	@rm -rf venv
	$(PYTHON) -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install twine

dist: libedit check/configure venv md-to-rst
	venv/bin/python3 setup.py sdist
