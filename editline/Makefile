
CC = gcc

PY3_BASE = /volume/diags/jde/python/3.3.0
LEDIT_BASE = /b/mnichols/libedit/install

all: readline.so  editline.so _editline.so

CFLAGS += -I$(PY3_BASE)/include/python3.3m -fPIC -O2 -D__APPLE__=1
CFLAGS += -I$(LEDIT_BASE)/include


readline.so: readline.o
	$(CC) -shared readline.o -L$(LEDIT_BASE)/lib -ledit -o readline.so 

editline.so: editline.o
	$(CC) -shared editline.o -L$(LEDIT_BASE)/lib -ledit -o editline.so 

_editline.so: _editline.o
	$(CC) -shared _editline.o -L$(LEDIT_BASE)/lib -ledit -o _editline.so 

clean:
	@rm -rf *.o *.so *~
