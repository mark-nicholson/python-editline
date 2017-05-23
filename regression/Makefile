




srcs:
	mkdir srcs


PYSITE=https://www.python.org/ftp/python

tarballs:
	mkdir tarballs
	wget -P tarballs $(PYSITE)/3.6.1/Python-3.6.1.tar.xz
	wget -P tarballs $(PYSITE)/3.5.3/Python-3.5.3.tar.xz
	wget -P tarballs $(PYSITE)/3.4.6/Python-3.4.6.tar.xz
	wget -P tarballs $(PYSITE)/3.3.6/Python-3.3.6.tar.xz
	wget -P tarballs $(PYSITE)/3.2.6/Python-3.2.6.tar.xz
	wget -P tarballs $(PYSITE)/3.1.5/Python-3.1.5.tar.xz
	wget -P tarballs http://thrysoee.dk/editline/libedit-20170329-3.1.tar.gz

Python-3.7.0a:
	tar -C srcs xf tarballs/Python-3.7.0a.tar.xz

Python-3.6.1:
	tar -C srcs xf tarballs/Python-3.6.1.tar.xz

Python-3.5.3:
	tar -C srcs xf tarballs/Python-3.5.3.tar.xz

Python-3.4.6:
	tar -C srcs xf tarballs/Python-3.4.6.tar.xz

Python-3.3.6:
	tar -C srcs xf tarballs/Python-3.3.6.tar.xz

# novenv
Python-3.2.6:
	tar -C srcs xf tarballs/Python-3.2.6.tar.xz

# no venv
Python-3.1.5:
	tar -C srcs xf tarballs/Python-3.1.5.tar.xz

extract: srcs Python-3.6.1 Python-3.5.3 Python-3.4.6 \
	   Python-3.3.6 
