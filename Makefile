#
#  Maintenance tool
#

all: libedit
	@echo "Done"

libedit:
	git clone git@github.com:mark-nicholson/libedit.git --branch release --single-branch libedit

clean:
	@$(MAKE) -C check clean
	@rm -rf build __pycache__
	@rm -f *~

distclean: clean
	@$(MAKE) -C check distclean
	@$(MAKE) -C libedit distclean
