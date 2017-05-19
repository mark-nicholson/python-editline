#!/usr/bin/env python3

"""
Prepare and install the libedit + editline support infrastructure.
"""

import sys
import os
from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext

from setupext.autoconf import ConfigureBuildExt, GeneralConfig

# collect the general configuration
gc = GeneralConfig()

#
# These are the basic build parameters
#
sources = [
    os.path.join('src', '_editline.c')
]
include_dirs = []
libraries = gc.get_libraries()
define_macros = []
cmdclass = {
    'build_ext': build_ext
}

# built-in libedit needed?
if gc.use_builtin_libedit():
    sources += [
        os.path.join('libedit', 'src', 'chared.c'),
        os.path.join('libedit', 'src', 'common.c'),
        os.path.join('libedit', 'src', 'el.c'),
        os.path.join('libedit', 'src', 'eln.c'),
        os.path.join('libedit', 'src', 'emacs.c'),
        os.path.join('libedit', 'src', 'hist.c'),
        os.path.join('libedit', 'src', 'keymacro.c'),
        os.path.join('libedit', 'src', 'map.c'),
        os.path.join('libedit', 'src', 'chartype.c'),
        os.path.join('libedit', 'src', 'parse.c'),
        os.path.join('libedit', 'src', 'prompt.c'),
        os.path.join('libedit', 'src', 'read.c'),
        os.path.join('libedit', 'src', 'refresh.c'),
        os.path.join('libedit', 'src', 'search.c'),
        os.path.join('libedit', 'src', 'sig.c'),
        os.path.join('libedit', 'src', 'terminal.c'),
        os.path.join('libedit', 'src', 'tty.c'),
        os.path.join('libedit', 'src', 'vi.c'),
        os.path.join('libedit', 'src', 'wcsdup.c'),
        os.path.join('libedit', 'src', 'tokenizer.c'),
        os.path.join('libedit', 'src', 'tokenizern.c'),
        os.path.join('libedit', 'src', 'history.c'),
        os.path.join('libedit', 'src', 'historyn.c'),
        os.path.join('libedit', 'src', 'filecomplete.c')
        ]

    include_dirs += [os.path.join('libedit', 'src'), 'libedit']
    define_macros = [('HAVE_CONFIG_H', None)]
    cmdclass['build_ext'] = ConfigureBuildExt


# termcap is needed on OpenBSD.
if sys.platform in ['openbsd6']:
    libraries.append('termcap')
elif sys.platform in ['sunos5']:
    libraries.append('ncurses')
elif sys.platform in ['linux']:
    libraries.append('tinfo')

#
# Define the basic extension parameters
#
editline_module = Extension(
    '_editline',
    sources=sources,
    libraries=libraries,
    include_dirs=include_dirs
)

#
# Run the setup mechanism
#
setup(name='_editline',
      version='1.0',
      description='Python modules to support libedit directly',
      ext_modules=[editline_module],

      py_modules=[
          'editline',
          'lineeditor',
          'test.test_editline',
          'test.test_lineeditor',
          'test.expty'
      ],

      cmdclass=cmdclass,

      url='http://sites.nicholnet.com',
      author='Mark Nicholson',
      author_email='nicholson.mark at gmail dot com')
