"""
Support to integrate autoconf's configure support to check for system
feature availability before generating a module.
"""

import sys
import os
import re
import tempfile

from distutils.command.build_ext import build_ext
from distutils.cmd import Command
from distutils.command.build import build
from distutils.command.build_clib import build_clib
from distutils.command.build_py import build_py
from distutils.command.install_lib import install_lib

# handy for debugging
from pprint import PrettyPrinter
pp = PrettyPrinter(indent=4)


class CarefulInstallLib(install_lib):
    """Handle sitecustomize.py better"""

    def install(self):
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
    """When building the package, ensure to try to maintain pre-existing
       sitecustomization.py support"""

    # kind of ugly, but no apparent other way...
    user_options = build_py.user_options + [
        ('merge-sitecustomize',
         None, "Force merge of old and new sitecustomize.py files"),
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
            nmf_data = nmf.read()

        # slurp the old info
        with open(scm.__file__) as scmf:
            scmf_data = scmf.read()

        # rewrite the new file with the merged contents
        with open(os.path.join(self.build_lib, module_file), 'w') as outf:
            outf.write(scmf_data)
            outf.write(padding)
            outf.write(nmf_data)
            outf.write(trailer)

        return rv



def parse_config_h(basedir, conf=None):
    """Parse the autoconf generated config.h file into a dict"""
    if conf is None:
        conf = {}
    with open(os.path.join(basedir, 'config.h')) as ch:
        print("parsing:", basedir, '/config.h')
        for line in ch.readlines():
            if line.startswith('#define'):
                parts = line.split()
                if len(parts) > 2:
                    conf[parts[1]] = parts[2].replace('"', '')
                else:
                    conf[parts[1]] = None
    return conf

def parse_autoconf(basedir, conf=None):
    """Parse the ac_cv_* values out of the log file..."""
    if conf is None:
        conf = {}
        
    section_found = False
    var_re = re.compile('^\w+=')
    
    with open(os.path.join(basedir, 'config.log')) as fd:
        print("parsing:", basedir, '/config.log')
        for line in fd.readlines():

            if not section_found:
                if 'cache variables' in line.lower():
                    section_found = True
                continue

            # grab the defines
            if line.startswith('#define'):
                parts = line.split()
                if len(parts) > 2:
                    conf[parts[1]] = parts[2].replace('"', '')
                else:
                    conf[parts[1]] = None
                continue

            # scoop up the variable assignments
            if var_re.match(line):
                line = line.rstrip()
                idx = line.index('=')
                tag = line[:idx]
                value = line[idx+1:]
                if value.startswith( ("'", '"') ):
                    value = value[1:]
                if value.endswith( ("'", '"') ):
                    value = value[:-1]
                conf[tag] = value
                #print("config.log: " + str(parts))
    return conf

def _run_cmd(cmd, tmpfile=None):
    """Run a system command, putting the output into a tmp file
    Return the system exit value
    """
    if tmpfile is None:
        tmpfile = tempfile.NamedTemporaryFile()
    cmd += " > {}".format(tmpfile.name)
    rv = os.system(cmd)
    if tmpfile:
        tmpfile.close()
    return rv

class GeneralConfig(object):
    """Class to manage the overall autoconf process."""
    
    def __init__(self, build_temp_dir, force_builtin=False):
        self.check_dir = os.path.join(build_temp_dir, 'check')
        self.force_builtin_libedit = force_builtin
        self.config = {}

        # setup the configure script
        cfs_path = os.path.relpath('src/check', self.check_dir)
        self.configure_script = os.path.join(cfs_path, 'configure')

        # create the basic build area
        path = ''
        for pathent in self.check_dir.split(os.path.sep):
            path = os.path.join(path, pathent)
            if not os.path.isdir(path):
                print("creating " + path)
                os.mkdir(path)

        # do the checking
        self.run_check()

    def run_check(self):
        """Fire off the configure.sh script, then parse the config.h file"""
        # run the configuration utility
        print("Running system inspection ...")
        check_cmd = 'cd ' + self.check_dir + '; /bin/sh ' + self.configure_script
        #print("run_check(): ", check_cmd)
        rv = _run_cmd(check_cmd)
        if rv != 0:
            raise Exception("Failed configuration ({})".format(rv))

        parse_config_h(self.check_dir, self.config)
        parse_autoconf(self.check_dir, self.config)

    def get_libraries(self):
        """Figure out what sort of system libraries are available"""
        libs = []
        
        if not self.use_builtin_libedit():
            libs.append( 'edit' )

        if 'ac_cv_link_lib_edit' not in self.config:
            return libs

        if self.config['ac_cv_link_lib_edit'] is None:
            return libs

        libs += self.config['ac_cv_link_lib_edit'].replace('-l', '').split()
        
        return libs 

    def use_builtin_libedit(self):
        """Decide if the system lib is adequate or if we need to build it in"""
        if self.force_builtin_libedit:
            return True
        if 'ac_cv_line_editor' not in self.config:
            return True
        if self.config['ac_cv_line_editor'] is None:
            return True
        if self.config['ac_cv_line_editor'] != "edit":
            return True
        return False


class ConfigureBuild(build):
    """Python build of builtin libedit"""

    # srcs required for the built-in libedit
    builtin_srcs = [
        'chared.c',
        'common.c',
        'el.c',
        'eln.c',
        'emacs.c',
        'hist.c',
        'keymacro.c',
        'map.c',
        'chartype.c',
        'parse.c',
        'prompt.c',
        'read.c',
        'refresh.c',
        'search.c',
        'sig.c',
        'terminal.c',
        'tty.c',
        'vi.c',
        'wcsdup.c',
        'tokenizer.c',
        'tokenizern.c',
        'history.c',
        'historyn.c',
        'filecomplete.c'
    ]

    # static dirs
    libedit_dir = os.path.join('src', 'libedit')
    libedit_src_dir = os.path.join('src', 'libedit', 'src')

    # option support
    user_options = build.user_options + [
        ('builtin-libedit', None, "Force use of builtin libedit"),
    ]
    boolean_options = build.boolean_options + ['builtin-libedit']

    def initialize_options(self):
        print("CB.initialize_options()")
        super().initialize_options()
        self.builtin_libedit = None

    def finalize_options(self):
        print("CB.finalize_options()")
        super().finalize_options()
        print("builtin_libedit =", self.builtin_libedit)

        # setup the builtin_libedit to a boolean value
        if self.builtin_libedit is None:
            self.builtin_libedit = False
        else:
            self.builtin_libedit = True


    def get_editline_extension(self):
        cext = None
        ext_name = 'editline._editline'

        for ce in self.distribution.ext_modules:
            if ce.name == ext_name:
                cext = ce
                break
            
        if cext is None:
            raise DistutilsSetupError("no definition of '{}' extension".format(ext_name))

        return cext
    
    def check_local_libedit(self, cext):
        # snoop the system for general stuff
        self._gc = GeneralConfig(self.build_temp, self.builtin_libedit)

        # basic builds just need a minor update then common code
        if not self._gc.use_builtin_libedit():
            print("Updating basic extension for localisation")
            cext.libraries += self._gc.get_libraries()
            return True

        # nope, nothing available
        return False

    def check_system(self):
        """Run the system inspection to create config.h"""

        #
        # For now, hack teh build with a hard-coded config.h and config.log
        #   Eventually, use Python to detect the needed stuff instead of
        #    using configure/autoconf
        #
        
        # setup a relative path to the configure script
        relpath = os.path.relpath(self.libedit_dir, self.conf_dir)
        conf_h_file = os.path.join(relpath, 'config.h')
        conf_log_file = os.path.join(relpath, 'config.log')

        os.symlink(conf_h_file, os.path.join(self.conf_dir, 'config.h'))
        os.symlink(conf_log_file, os.path.join(self.conf_dir, 'config.log'))


    def configure_builtin_libedit(self, ext):

        print("Reconfiguring for builtin libedit")

        # setup common paths
        self.conf_dir = os.path.join(self.build_temp, self.libedit_dir)
        self.build_src_dir = os.path.join(self.conf_dir, 'src')

        # update to append the additional sources
        for srcfile in self.builtin_srcs:
            ext.sources.append(os.path.join(self.libedit_src_dir, srcfile))

        # add these to match the new srcs
        ext.include_dirs += [
            os.path.join(self.libedit_dir, 'gen'),
            os.path.join(self.libedit_src_dir)
        ]

        # we'll cook up a config.h
        ext.define_macros += [('HAVE_CONFIG_H', None)]
        
        # create the basic build area
        print("creating " + self.conf_dir)
        os.makedirs(self.conf_dir, exist_ok=True)

        # generate the config* files
        self.check_system()

        # grab the settings
        config = {}
        parse_config_h(self.conf_dir, config)
        parse_autoconf(self.conf_dir, config)

        # these are based on detection
        if 'HAVE_STRLCPY' not in config:
            ext.sources.append(os.path.join(self.libedit_src_dir, 'strlcpy.c'))
        if 'HAVE_STRLCAT' not in config:
            ext.sources.append(os.path.join(self.libedit_src_dir, 'strlcat.c'))
        if 'HAVE_VIS' not in config:
            ext.sources.append(os.path.join(self.libedit_src_dir, 'vis.c'))
        if 'HAVE_UNVIS' not in config:
            ext.sources.append(os.path.join(self.libedit_src_dir, 'unvis.c'))

        # add an include dir for config.h
        ext.include_dirs.append(self.conf_dir)

        # add any needed libraries found in the built-in configuration
        ext.libraries += config['LIBS'].replace('-l', '').split()

        # done
        return

    def run(self):
        print("CB.run()")

        # locate the extension 
        cext = self.get_editline_extension()

        # check for the locally installed library
        found = self.check_local_libedit(cext)

        # setup the internal build if necessary
        if not found:
            self.configure_builtin_libedit(cext)

        # now run the common build
        super().run()


class ConfigureBuildCLib(build_clib):
    """Python build of builtin libedit"""

    def initialize_options(self):
        print("CBCLib.initialize_options()")
        super().initialize_options()

    def finalize_options(self):
        print("CBCLib.finalize_options()")
        super().finalize_options()

    def run(self):
        print("CBCLib.run()")
        super().run()


class ConfigureBuildExt(build_ext):
    """Build extension to run autoconf configure.sh"""
    
    def run(self):
        # mostly do the common stuff
        super().run()

    def build_extension(self, ext):
        """Override this routine to run our custom autoconf crap"""
        # build as normal
        super().build_extension(ext)
