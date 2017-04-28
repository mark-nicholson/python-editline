#
#  Maintenance tool
#

all:
	@echo "Nothing to build"

clean:
	@make -C check clean
	@rm -rf build __pycache__
	@rm -f *~

distclean: clean
	@make -C check distclean
	@make -C libedit distclean
