#!/usr/bin/env python3

"""
Prepare and install the libedit + editline support infrastructure.
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
    name='_editline',
    version='1.0',
    description='Python modules to support libedit directly',
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

    url='http://sites.nicholnet.com',
    author='Mark Nicholson',
    author_email='nicholson.mark at gmail dot com'
)
