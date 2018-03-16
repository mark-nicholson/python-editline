#
#  Prepare the sources for the build.
#

REGR_DIR=$(PWD)
PATCH_DIR=$(shell dirname $(PWD))/patches
BASEDIR=$(shell dirname $(PWD))

PYSITE=https://www.python.org/ftp/python

PY37_VER=3.7.0b2
PY36_VER=3.6.4
PY35_VER=3.5.5
PY34_VER=3.4.7

GAWK_VER=4.1.4

all: \
	srcs/libedit \
	srcs/libffi \
	srcs/gawk-$(GAWK_VER) \
	srcs/Python-$(PY37_VER) \
	srcs/Python-$(PY36_VER) \
	srcs/Python-$(PY35_VER) \
	srcs/Python-$(PY34_VER)

srcs:
	mkdir srcs

tarballs:
	mkdir tarballs


tarballs/Python-$(PY37_VER).tar.xz: tarballs
	wget -P tarballs $(PYSITE)/3.7.0/Python-$(PY37_VER).tar.xz

srcs/Python-$(PY37_VER): tarballs/Python-$(PY37_VER).tar.xz
	tar -C srcs -xf tarballs/Python-$(PY37_VER).tar.xz
	cd srcs/Python$(PY37_VER) && patch -p1 < $(PATCH_DIR)/main.c.patch

tarballs/Python-$(PY36_VER).tar.xz: tarballs
	wget -P tarballs $(PYSITE)/$(PY36_VER)/Python-$(PY36_VER).tar.xz

srcs/Python-$(PY36_VER): tarballs/Python-$(PY36_VER).tar.xz
	tar -C srcs -xf tarballs/Python-$(PY36_VER).tar.xz
	cd srcs/Python$(PY36_VER) && patch -p1 < $(PATCH_DIR)/main.c.patch

tarballs/Python-$(PY35_VER).tar.xz: tarballs
	wget -P tarballs $(PYSITE)/$(PY35_VER)/Python-$(PY35_VER).tar.xz

srcs/Python-$(PY35_VER): tarballs/Python-$(PY35_VER).tar.xz
	tar -C srcs -xf tarballs/Python-$(PY35_VER).tar.xz
	cd srcs/Python$(PY35_VER) && patch -p1 < $(PATCH_DIR)/main.c.patch

tarballs/Python-$(PY34_VER).tar.xz: tarballs
	wget -P tarballs $(PYSITE)/$(PY34_VER)/Python-$(PY34_VER).tar.xz

srcs/Python-$(PY34_VER): tarballs/Python-$(PY34_VER).tar.xz
	tar -C srcs -xf tarballs/Python-$(PY34_VER).tar.xz
	cd srcs/Python$(PY34_VER) && patch -p1 < $(PATCH_DIR)/main.c.patch

tarballs/gawk-$(GAWK_VER).tar.xz:
	wget -P tarballs http://ftp.gnu.org/gnu/gawk/gawk-$(GAWK_VER).tar.xz

srcs/gawk-$(GAWK_VER): srcs tarballs/gawk-$(GAWK_VER).tar.xz
	tar -C srcs -xf tarballs/gawk-$(GAWK_VER).tar.xz

srcs/libedit: srcs
	rm -rf srcs/libedit
	git clone git@github.com:mark-nicholson/libedit.git --branch release --single-branch srcs/libedit

srcs/libffi: srcs
	rm -rf srcs/libffi
	git clone git@github.com:libffi/libffi.git srcs/libffi

