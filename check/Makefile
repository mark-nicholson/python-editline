

all:
	autoconf
	autoheader

CHECK_DIRT = \
	config.log \
	config.status \
	autom4te.cache
CHECK_DISTCLEAN = \
	configure \
	config.h

clean:
	@rm -f *~
	@rm -rf ${CHECK_DIRT}

distclean: clean
	@rm -rf ${CHECK_DISTCLEAN}
