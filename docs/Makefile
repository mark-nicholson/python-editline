# Minimal makefile for Sphinx documentation
#   Handy Guide: https://samnicholls.net/2016/06/15/how-to-sphinx-readthedocs/
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINX_APIDOC = sphinx-apidoc
SPHINXPROJ    = EditLine
SOURCEDIR     = .
BUILDDIR      = _build
EXCLUDES      = ../editline/tests ../hostconf ../setup.py ../setupext
TOPDIR        = ../

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -b help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

api-docs:
	@$(SPHINX_APIDOC) -o source $(TOPDIR) $(EXCLUDES) 

api-clean:
	@rm -f source/*

clean:
	@rm -rf _build

distclean: clean

vars:
	@echo @$(SPHINXBUILD) -b $@ -v "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile api-docs api-clean clean distclean

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -b $@ -v "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
