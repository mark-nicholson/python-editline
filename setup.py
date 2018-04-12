#!/usr/bin/env python3

# ensure it is in ReST so PyPI is happy
"""
Python-Editline
===============

This is a package which is a replacement for GNU Readline for use as shell-completion support. It is designed to:

- link to libedit.so on the host system
  (This covers most \*BSD based systems and Linux if you install libedit2 package)
- if no host libedit.so is available, libedit will be directly compiled into the extension itself

All code is released under the BSD-3 license, which makes this an alternative in cases where GNU-based readline is a problem.

Usage
-----

After a standard, uneventful installation, you should automatically have tab-completion using editline.  This is configured in a sitecustomize.py file added to your install or virtual-env.

This extension has more extensive features than readline such as:

- tab-completion of imports by default
- tab-completion across arrays (so you can see/pick a valid index)
- tab-completion across dictionaries (displays available keys)
- Right-side prompts
- Arbitrary input/output/error streams so you can have multiple interpreters on a single Python instance which are fully independent. ('readline' uses C globals so you are stuck with just one instance)

The system is broken down in 3 components:

:_editline.so:
   the C interface to libedit
:editline.py:
   a Python subclass of _editline which implements much of the string parsing/manipulation
:lineeditor.py:
   a general module which extends rlcompleter's functionality and provides additional features.

Again, by default this is entirely hidden.


Installation
------------

Handy tips for installation.  99.9% of folks will be able to use the default install (... by SDIST!).  It will customize your build based on finding stuff.

In the (odd) case where you have libedit.so and you *really* want to have editline use the built-in version (say, your distro's libedit.so is borked) you can adjust the installer.

Run the pip install like this::

  pip install \
       --global-option="build_ext" \
       --global-option="--builtin-libedit"  pyeditline

That will bypass the use of your local libedit.so.  (... and if anyone has a better way to do this, I'm all ears.)

Gory Details?
-------------

Have a look at the README.md in the source repo.

"""

import sys
import os
from distutils.core import setup, Extension

from setupext.autoconf import *

import editline

#
# Define the basic extension parameters
#   Overriding may take place in the build-extension
#

#
# Run the setup mechanism
#
setup(
    name='pyeditline',
    version=editline.version(),
    description='A fully functional command-line completion module built '
                'to directly interface with libedit.',
    long_description=__doc__,
    ext_modules=[
        Extension(
            'editline._editline',
            sources=[
                os.path.join('src', '_editline.c')
            ],
            define_macros = [],
            include_dirs = [],
            libraries = []
        )
    ],
    libraries=[],
    packages=[
        'editline',
        'editline.tests',
        'editline.tests.support'
    ],
    py_modules=[
        'sitecustomize'
    ],
    cmdclass = {
        'build': ConfigureBuild,
        'build_ext': OptimizeBuildExt,
        'build_py': MergeBuildPy,
        'install_lib': CarefulInstallLib
    },
    url='https://github.com/mark-nicholson/python-editline',
    author='Mark Nicholson',
    author_email='nicholson.mark@gmail.com',
    license='BSD',
    python_requires='>=3.3',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Programming Language :: C',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ]
)
