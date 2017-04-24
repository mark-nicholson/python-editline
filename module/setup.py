#!/usr/bin/env python3

from distutils.core import setup, Extension

editline_module = Extension(
    '_editline',
    sources = ['_editline.c'],
    libraries = ['edit']
)

setup(name = '_editline',
      version = '1.0',
      description = 'Python module to support libedit directly',
      ext_modules = [editline_module],

      url='http://sites.nicholnet.com',
      author='Mark Nicholson',
      author_email='nicholson.mark at gmail dot com')
