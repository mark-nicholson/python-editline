#
#  Maintenance tool
#

PYTHON?=/work/mjn/python/python-editline/regression/ubuntu-16.04.4/install-3.6.4/bin/python3

all: src/libedit src/check/configure
	@echo "Done"

src/libedit:
	git clone git@github.com:mark-nicholson/libedit.git --branch release --single-branch src/libedit

src/check/configure:
	$(MAKE) -C src/check

md-to-rst:
	pandoc --from=markdown --to=rst --output README.rst README.md

clean:
	@$(MAKE) -C src/check clean
	@rm -rf build __pycache__
	@rm -f *~ README.rst MANIFEST

distclean: clean
	@$(MAKE) -C src/check distclean
	@rm -rf src/libedit
	@rm -rf venv dist

venv:
	@rm -rf venv
	$(PYTHON) -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install twine

dist: src/libedit src/check/configure venv md-to-rst
	venv/bin/python3 setup.py sdist

clean-venv:
	@find venv/lib/python3.5/site-packages/ -name '*edit*' | xargs /bin/rm -rf
	@rm venv/lib/python3.5/site-packages/sitecustomize.py*
