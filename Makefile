#
#  Maintenance tool
#

LIBEDIT_SRC=libedit-20170329-3.1
LIBEDIT_URL=http://thrysoee.dk/editline/${LIBEDIT_SRC}.tar.gz

all: libedit
	@echo "Done"

/tmp/${LIBEDIT_SRC}.tar.gz:
	wget -P /tmp ${LIBEDIT_URL}

libedit: /tmp/${LIBEDIT_SRC}.tar.gz
	tar xf /tmp/${LIBEDIT_SRC}.tar.gz
	mv ${LIBEDIT_SRC} libedit

clean:
	@make -C check clean
	@rm -rf build __pycache__
	@rm -f *~

distclean: clean
	@make -C check distclean
	@make -C libedit distclean
