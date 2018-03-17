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

First, download and extract the source tarball or clone from the repo.

Run the installer manually like this::

  python3 setup.py build --builtin-libedit
  python3 setup.py install


That will bypass the use of your local libedit.so.

Gory Details?
-------------

Have a look at the README.md in the source repo.

"""

import sys
import os
from distutils.core import setup, Extension
from distutils.cmd import Command
from distutils.command.build_ext import build_ext
from distutils.command.build_py import build_py
from distutils.command.install_lib import install_lib

from setupext.autoconf import ConfigureBuildExt, GeneralConfig

class CarefulInstallLib(install_lib):
    """Handle sitecustomize.py better"""

    def install(self):
        print("CIL:install()")
        sc_path = os.path.join(self.install_dir, 'sitecustomize.py') 

        # original sitecustomize there?
        if os.path.isfile(sc_path):
            # keep the last one as a reference
            if os.path.isfile(sc_path + '.orig'):
                os.remove(sc_path + '.orig')
            os.rename(sc_path, sc_path + '.orig')
            print("Found pre-existing sitecustomize.py file... saving")

        # normal ops now 
        super().install()


class MergeBuildPy(build_py):

    # kind of ugly, but no apparent other way...
    user_options = build_py.user_options + [
        ('merge-sitecustomize', None, "Force merge of old and new sitecustomize.py files"),
    ]
    boolean_options = build_py.boolean_options + ['merge-sitecustomize']

    def initialize_options(self):
        super().initialize_options()
        self.merge_sitecustomize = False

    def finalize_options(self):
        super().finalize_options()
        self.set_undefined_options('build',
                                   ('merge_sitecustomize',
                                    'merge_sitecustomize'))

    def build_module(self, module, module_file, package):

        # run the parent to do the basic setup
        rv = super().build_module(module, module_file, package)

        # ignore other stuff
        if module != 'sitecustomize' or 'sitecustomize' not in sys.modules:
            return rv

        # notice...
        if not self.merge_sitecustomize:
            print("NOTICE: you have a pre-existing sitecustomize.py file!")
            print("        Manual customization to incorporate necessary")
            print("        changes is on you.")
            print("        Use '--merge-sitecustomize' on build_py stage")
            print("        and the files will merged.")
            return rv
        
        # create some section headings
        padding = '\n'.join([
            '',
            '#### start editline siteconfig ####',
            ''
        ])
        trailer = '\n'.join([
            '',
            '#### end editline siteconfig ####',
            ''
        ])

        # grab the module
        scm = sys.modules['sitecustomize']

        # slurp the new info
        with open(os.path.join(self.build_lib, module_file)) as nmf:
            print("MBP: reading new sitecustomize")
            nmf_data = nmf.read()

        # slurp the old info
        with open(scm.__file__) as scmf:
            print("MBP: reading old sitecustomize")
            scmf_data = scmf.read()

        # rewrite the new file with the merged contents
        with open(os.path.join(self.build_lib, module_file), 'w') as outf:
            print("MPB: merging ...")
            outf.write(scmf_data)
            outf.write(padding)
            outf.write(nmf_data)
            outf.write(trailer)

        return rv
            


class CleanUp(Command):

    description = "Clean out a pre-existing installation"
    user_options = [
        ('force', 'f', "forcibly remove everything"),
        ]

    def initialize_options(self):
        self.force = False

    def finalize_options(self):
        pass

    def run(self):
        print("CleanUp:run()")

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
    'build_ext': build_ext,
    'build_py': MergeBuildPy,
    'install_lib': CarefulInstallLib,
    'clean': CleanUp
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

    libraries = []
    include_dirs += [os.path.join('libedit', 'src'), 'libedit']
    define_macros = [('HAVE_CONFIG_H', None)]
    cmdclass['build_ext'] = ConfigureBuildExt


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
setup(
    name='editline',
    version='0.1.0',
    description='A fully functional command-line completion module built '
                'to directly interface with libedit.',
    long_description=__doc__,

    ext_modules=[editline_module],
    
    py_modules=[
        'editline',
        'lineeditor',
        'sitecustomize',
        'test.test_editline',
        'test.test_lineeditor',
        'test.expty'
    ],
      
    cmdclass=cmdclass,

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
