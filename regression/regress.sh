#!/bin/sh
#
# Usage: infra.sh cmd <options>
#
# Regression infrastructure script to test the Python editline extension.
#   - Builds various versions of Python interpreters
#   - Creates virtual-envs to test the 3 configurations of editline
#       1. Distribution:  /usr/lib/libedit.so
#       2. Built-In:      integrated libedit directly in editline.so
#       3. Custom:        Stand-alone build of AutoTool'ed NetBSD libedit
#   - Runs the unittest of all tests/test_*.py files for editline package
#     on each virtualenv
#
# Commands:
#    build      - build Python interpreters
#    libedit    - build custom libedit install
#    gawk       - build a reputable version of GAWK
#    venv|venvs - create the VENVs
#    install    - install editline package into the VENVs
#    check      - run the unittest
#    vars       - show some internal variables
#    help       - this message
#
# Environment:
#   PIP_PKG - path to pyeditline pip package
#   VER     - list of Python versions to work on (quote multiple)
#   CFG     - specify a configuration to work on (default: 'dist builtin custom')
#   SRCS    - base directory of unpacked source code
#   GAWK    - specify the GAWK to use
#   SED     - specify the SED to use
#
#
# Notes:
#   For the 'check' command, the best sequence is this:
#     $ script test.log
#     $ infra.sh check
#     $ exit
###

PWD=$(pwd)

PY_VERSIONS=${VER:-"3.4.8 3.5.5 3.6.5 3.7.0b4"}
CONFIGURATIONS=${CFG:-"dist builtin custom"}

SRCS=${SRCS:-${PWD}/srcs}

PIP_PKG=${PIP_PKG:-../dist/pyeditline-1.9.4.tar.gz}

LIBEDIT=${PWD}/libedit
LIBEDIT_SRC=${LIBEDIT_SRC:-${SRCS}/libedit}

GAWK=${GAWK:-gawk}
GAWK_VER=4.1.4
GAWK_DIR=${PWD}/gawk
GAWK_SRC=${GAWK_SRC:-${SRCS}/gawk-${GAWK_VER}}

SED=${SED:-sed}

force=${force:-0}

HOST_TYPE=$(uname)

# update the PATH to grab the local gawk -- a dud entry is ok
export PATH=${GAWK_DIR}/bin:${PATH}

usage()
{
    sed -n -E -e '2,/^###/ p' $0 | sed -E 's/^#+//'
    exit 0
}

banner()
{
    echo 
    echo "******************************************************"
    echo "*"
    echo "*      $1"
    echo "*"
    echo "******************************************************"
}

build_python()
{
    ver=$1

    # status...
    banner "Building Python ${ver}"
	
    # manage pre-existing stuff
    if [ -d ${ver} ]; then
	if [ $force == "1" ]; then
	    rm -rf ${ver}
	else
	    echo "    Skipping -- already built"
	    continue
	fi
    fi

    case ${HOST_TYPE} in
	OpenBSD)
	    CONFIG_OPTS="--with-system-ffi"
	    ;;
	Darwin)
	    CONFIG_OPTS="MACOS_DEPLOYMENT_TARGET=10.12 --enable-ipv6 --enable-loadable-sqlite-extensions --with-dtrace --without-gcc"
	    ;;
	*)
	    CONFIG_OPTS=
	    ;;
    esac

    pydir=${PWD}/${ver}

    # cook it up
    (
	export CPPFLAGS=-I/usr/local/include
	export LDFLAGS=-L/usr/local/lib
	
	mkdir -p ${pydir}/build
	cd ${pydir}/build

	${SRCS}/Python-${ver}/configure \
	       --prefix ${pydir} ${CONFIG_OPTS} | tee build.config.log

	make | tee build.make.log
	make install | tee build.install.log 

	cd ../..
    )
    
    echo
}

platform_verify()
{
    case ${HOST_TYPE} in
	Darwin)
	    echo "Ensure we have command-line tools"
	    echo "Ensure we have 'homebrew'"
	    echo "Homebrew install python (and its dependencies ...) openssh/openssl"

	    # cross-link the includes
	    cd /usr/local/include
	    ln -s ../Cellar/openssl/1.0.2o_1/include/openssl

	    # cross-link the libs  (brew really should do this...)
	    cd /usr/local/lib
	    for item in libssl libcrypto; do
		ln -s ../Cellar/openssl/1.0.2o_1/lib/${item}.a
		ln -s ../Cellar/openssl/1.0.2o_1/lib/${item}.dylib
		ln -s ../Cellar/openssl/1.0.2o_1/lib/${item}.1.0.0.dylib
	    done
	    ;;

	Linux)
	    echo "Install libedit,libedit-dev packages"
	    ;;
	
	*)
	    echo "Unsupported platform"
	    ;;
    esac
}

build_pythons()
{
    for ver in ${PY_VERSIONS}; do

	build_python ${ver}

    done
}

build_venv()
{
    ver=$1
    cfg=$2

    # define the naming convention
    venv=venv-${ver}-${cfg}

    # pre-existing?
    if [ -d ${venv} ]; then
	echo "   Using pre-built ${venv}"
	return 
    fi

    # status...
    banner "Building virtual-env for ${venv}"

    # manage pre-existing stuff
    if [ -d ${venv} ]; then
	if [ $force == "1" ]; then
	    rm -rf ${venv}
	else
	    echo "    Skipping"
	    echo ""
	    return
	fi
    fi

    # cook it up
    ./${ver}/bin/python3 -m venv ${venv}

    # tweak it
    venv-${ver}-${cfg}/bin/pip install --upgrade pip

    echo	    
}

build_venvs()
{
    for ver in ${PY_VERSIONS}; do

	# dependency check...
	if [ ! -d ${ver} ]; then
	    build_python ${ver}
	fi

	for cfg in ${CONFIGURATIONS}; do

	    build_venv ${ver} ${cfg}

	done

    done
}

install_editline()
{
    # make sure we have a distro
    if [ "x${PIP_PKG}" = "x" -o ! -e ${PIP_PKG} ]; then
	echo "ERROR: must specify a valid PyEditline distribution"
	exit -2
    fi

    # dependency
    build_libedit

    # paste it into each venv
    for ver in ${PY_VERSIONS}; do

	for cfg in ${CONFIGURATIONS}; do

	    # define the naming convention
	    venv=venv-${ver}-${cfg}

	    # dependency check...
	    build_venv ${ver} ${cfg}

	    # status...
	    banner "Installing PyEditline into ${venv}"

	    # install the dist...
	    case ${cfg} in
		dist)
		    venv-${ver}-${cfg}/bin/pip install ${PIP_PKG}
		    ;;
		
		builtin)
		    venv-${ver}-${cfg}/bin/pip install \
			 --global-option="build" \
			 --global-option="--builtin-libedit" \
			 ${PIP_PKG}
		    ;;

		custom)
		    CFLAGS=-I${LIBEDIT}/include LDFLAGS=-L${LIBEDIT}/lib \
			  venv-${ver}-${cfg}/bin/pip install ${PIP_PKG}
		    ;;
	    esac

	    echo ""
	    
	done

    done
}

build_libedit()
{
    if [ "x${LIBEDIT_SRC}" = "x" ]; then
	echo "Must define LIBEDIT_SRC"
	exit -3
    fi

    build_gawk

    if [ -d ${LIBEDIT} ]; then
	echo "   Using existing ${LIBEDIT} build"
	return
    fi
    
    (
	mkdir -p ${LIBEDIT}/build
	cd ${LIBEDIT}/build
	${LIBEDIT_SRC}/configure --prefix ${LIBEDIT}
	make
	make install
	cd ../..
    )
}

build_gawk()
{
    gawk_ver=$(gawk --version | head -n 1 | awk '{print $3;}')

    case ${gawk_ver} in
	4.*|5.*|6.*)
	    echo "   GAWK ${gawk_ver} works ..."
	    return
	    ;;
	*)
	    echo "   GAWK -- need upgraded version "
	    ;;
    esac

    (
	mkdir -p ${GAWK_DIR}/build
	cd ${GAWK_DIR}/build
	${GAWK_SRC}/configure --prefix ${GAWK_DIR}
	make
	make install
	cd ../..
	export GAWK=${GAWK_DIR}/bin/gawk
    )
}

TEST_FILES="test_editline.py \
            test_lineeditor.py \
            test_list_completion.py \
            test_dict_completion.py"

test_editline_venv()
{
    venv=$1
    
    banner "Testing ${venv}"

    # isolate the python version
    version=`echo ${venv} | ${SED} -E -e 's/^venv-//' -e 's/-.+$//'`
    ver_2tuple=`echo ${version} | ${SED} -E 's/\.[0-9]b?.?$//'`

    # use the test files *in* the installation
    tests_path=${venv}/lib/python${ver_2tuple}/site-packages/editline/tests
    
    logfile=${venv}/results_${version}.log

    # prep the environment
    case ${venv} in
	*-custom)
	    link_env=LD_LIBRARY_PATH=${LIBEDIT}/lib
	    ;;

	*-dist|*-builtin)
	    link_env=BOGUS=unused
	    ;;

	*)
	    echo "   INVALID venv"
	    continue
	    ;;
    esac

    # run the testing...
    (
	export ${link_env}
	for tf in ${TEST_FILES}; do
	    echo "*** $tf"
	    ${venv}/bin/python3 ${tests_path}/${tf}
	done
    )
    
    echo "done"
}

test_editline()
{
    for ver in ${PY_VERSIONS}; do

	for cfg in ${CONFIGURATIONS}; do

	    test_editline_venv venv-${ver}-${cfg}

	done

    done

}

PYSITE=https://www.python.org/ftp/python

collect_wget()
{
    wget -P $1 $2
}

collect_fetch()
{
    fetch -o $1 $2
}

collect_curl()
{
    fname=`basename $2`
    curl -o ${1}/${fname} $2
}

collect_sources()
{
    mkdir -p tarballs
    mkdir -p srcs

    case ${HOST_TYPE} in
	NetBSD)
	    GETTER=collect_fetch
	    ;;	
	Darwin|SunOS)
	    GETTER=collect_curl
	    ;;	
	*)
	    GETTER=collect_wget
	    ;;
    esac

    for version in ${PY_VERSIONS}; do

	# need some re-arrangements of the version 
	ver_3tuple=`echo ${version} | ${SED} -E 's/b[0-9]+$//'`
	ver_2tuple=`echo ${version} | ${SED} -E 's/\.[0-9]b?.?$//'`
	ver_2d=`echo ${ver_2tuple} | ${SED} 's/\.//'`

	echo "Collecting Python ${version}"

	# collect the tarball
	if [ ! -f tarballs/Python-${version}.tar.xz ]; then
	    ${GETTER} tarballs ${PYSITE}/${ver_3tuple}/Python-${version}.tar.xz
	fi
	
	# extract it
	if [ ! -d srcs/Python-${version} ]; then
	    #tar -C srcs --xz -xf tarballs/Python-${version}.tar.xz
	    xzcat tarballs/Python-${version}.tar.xz | tar -C srcs -xf -
	
	    # patching...
	    (
		cd srcs/Python-${version}
		patch -p1 < ${SRCS}/../patches/python${ver_2d}_main.patch
		cd ..
	    )
	fi
	
    done

    # pip... just in case
    if [ ! -f tarballs/get-pip.py ]; then
	${GETTER} tarballs https://bootstrap.pypa.io/get-pip.py
    fi

    # libedit
    if [ ! -f tarballs/libedit-20170329-3.1.tar.gz ]; then
	${GETTER} tarballs http://thrysoee.dk/editline/libedit-20170329-3.1.tar.gz
    fi
    if [ ! -d src/libedit ]; then
	tar -C srcs -xzf tarballs/libedit-20170329-3.1.tar.gz
	mv srcs/libedit-20170329-3.1 srcs/libedit
    fi

    # gawk
    if [ ! -f tarballs/gawk-${GAWK_VER}.tar.xz ]; then
	${GETTER} tarballs http://ftp.gnu.org/gnu/gawk/gawk-${GAWK_VER}.tar.xz
    fi
    if [ ! -d srcs/gawk-${GAWK_VER} ]; then
	xzcat tarballs/gawk-${GAWK_VER}.tar.xz | tar -C srcs -xf -
    fi
}


#
#  Rummage through the options...
#

if [ ${HOST_TYPE} = "SunOS" ]; then
    PATH=/usr/gnu/bin:$PATH
fi

# make sure SED can handle -E
echo venv-VER-crap | ${SED} -E -e 's/^venv-//' > /dev/null 2>&1
if [ $? != "0" ]; then
    echo "Updating sed ..."
    SED=gsed
fi

#
#  Manage the commands
#
case $1 in

    build)
	build_pythons
	;;

    libedit)
	build_libedit
	;;

    gawk)
	build_gawk
	;;

    venv)
	build_venv ${PY_VERSIONS} ${CONFIGURATIONS}
	;;

    venvs)
	build_venvs ${PY_VERSIONS}
	;;

    install)
	install_editline ${PY_VERSIONS}
	;;

    check)
	test_editline ${PY_VERSIONS}
	;;

    vars)
	echo ""
	echo "Host Type:      ${HOST_TYPE}"
	echo "Versions:       ${PY_VERSIONS}"
	echo "Configurations: ${CONFIGURATIONS}"
	echo "PIP Pkg:        ${PIP_PKG}"
	echo "force:          $force"
	echo ""
	;;

    fetch)
	collect_sources
	;;

    help)
	usage main
	;;
    
    *)
	echo "Unknown command"
	exit 1
	;;

esac
