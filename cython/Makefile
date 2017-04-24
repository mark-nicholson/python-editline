#
#  Makefile to setup the dev environment
#

ROOT := $(PWD)
VENV := $(ROOT)/venv
LIBEDIT_DIR := $(ROOT)/libedit

export PATH := $(VENV)/bin:$(PATH)

LIBEDIT_TAG = libedit-20140213-3.1
LIBEDIT_TGZ = libedit-20140213-3.1.tar.gz

CC = gcc
PY_VER = 3.3m
PY_BASE = /home/mjnichol/tools

all: prep install-editline editline/build 

prep: $(LIBEDIT_DIR)/build

install-editline:
	python3 setup.py install

venv $(VENV):
	pyvenv --system-site-packages $@

libedit $(LIBEDIT_DIR):
	mkdir -p $@

$(LIBEDIT_DIR)/$(LIBEDIT_TGZ): $(LIBEDIT_DIR)
	cp /import/rapid/platform-software/downloads/$(LIBEDIT_TGZ) $@
#	cd libedit && wget libedit-20140213-3.1.tar.gz

$(LIBEDIT_DIR)/$(LIBEDIT_TAG): $(LIBEDIT_DIR)/$(LIBEDIT_TGZ)
	cd $(LIBEDIT_DIR) && tar xf $(LIBEDIT_TGZ)
	echo 'extern VFunction	*rl_event_hook;' >> $(LIBEDIT_DIR)/$(LIBEDIT_TAG)/src/editline/readline.h
	touch $@

$(LIBEDIT_DIR)/build: $(VENV) $(LIBEDIT_DIR)/$(LIBEDIT_TAG)
	mkdir $(LIBEDIT_DIR)/build
	cd $(LIBEDIT_DIR)/build && ../libedit-20140213-3.1/configure --prefix=$(VENV)
	cd $(LIBEDIT_DIR)/build && make
	cd $(LIBEDIT_DIR)/build && make install
	touch $@/.done


# common bits for everybody
CFLAGS += -pthread -Wno-unused-result -DNDEBUG -g -fwrapv -O3 -Wall -Wstrict-prototypes -fPIC
CFLAGS += -I$(VENV)/include -I$(PY_BASE)/include/python$(PY_VER)
LDFLAGS += -shared -L$(VENV)/lib -ledit

#
#  Direct build of items
#
editline/readline.o: editline/readline.c
	$(CC) $(CFLAGS) -c -D__APPLE__=1 -o $@ $< 

# std readline extension built with libedit
editline/readline.so: editline/readline.o
	$(LD) $(LDFLAGS) -o $@ $<


# Cython extension
editline/editline.c: editline/editline.pyx
	cython -I$(ROOT) -I$(ROOT)/editline -o $@ $<

editline/editline.so: editline/editline.o
	$(LD) $(LDFLAGS) -o $@ $<

# all C implementation
editline/_editline.so: editline/_editline.o
	$(LD) $(LDFLAGS) -o $@ $< 

editline/build: editline/_editline.so editline/readline.so editline/editline.so

editline/clean:
	@rm -rf editline/editline.c editline/*.o editline/*.so editline/*~ editline/__pycache__

clean: editline/clean
	@rm -f *~ *.bak
	@rm -rf build $(LIBEDIT_DIR)/build $(LIBEDIT_DIR)/libedit-20140213-3.1

distclean: clean
	@rm -rf $(VENV) $(LIBEDIT_DIR)
