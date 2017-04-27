#!/usr/bin/env python3

import sys
from distutils.core import setup, Extension



libraries = [ 'edit' ]

# termcap is needed on OpenBSD.
if sys.platform in [ 'openbsd6' ]:
    libraries.append( 'termcap' )

# add additional library quirks

editline_module = Extension(
    '_editline',
    sources = ['_editline.c'],
    libraries = libraries
)


setup(name = '_editline',
      version = '1.0',
      description = 'Python module to support libedit directly',
      ext_modules = [editline_module],

      url='http://sites.nicholnet.com',
      author='Mark Nicholson',
      author_email='nicholson.mark at gmail dot com')
