"""
Support to integrate autoconf's configure support to check for system
feature availability before generating a module.
"""

import sys
import os
import re
import tempfile
from pprint import PrettyPrinter

from distutils.command.build_ext import build_ext

pp = PrettyPrinter(indent=4)

def parse_config_h(basedir, conf=None):
    """Parse the autoconf generated config.h file into a dict"""
    if conf is None:
        conf = {}
    with open(os.path.join(basedir, 'config.h')) as ch:
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
    
    def __init__(self):
        self.check_dir = 'check'
        self.configure_script = 'configure'
        self.force_builtin_libedit = False
        self.config = {}
        
        for i, arg in enumerate(sys.argv):
            if arg == '--builtin-libedit':
                self.force_builtin_libedit = True
                del sys.argv[i]

        self.run_check()

    def run_check(self):
        """Fire off the configure.sh script, then parse the config.h file"""
        # run the configuration utility
        print("Running system inspection ...")
        rv = _run_cmd('cd ' + self.check_dir + '; /bin/sh ' + self.configure_script)
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


class ConfigureBuildExt(build_ext):
    """Build extension to run autoconf configure.sh"""

    def build_extension(self, ext):
        """Override this routine to run our custom autoconf crap"""
        print("  build-temp: " + self.build_temp)

        # create the basic build area
        path = ''
        for pathent in self.build_temp.split(os.path.sep):
            path = os.path.join(path, pathent)
            if not os.path.isdir(path):
                print("creating " + path)
                os.mkdir(path)

        # make the configure area
        conf_dir = os.path.join(self.build_temp, 'libedit')
        print("creating " + conf_dir)
        os.mkdir(conf_dir)

        relpath = os.path.relpath('libedit', conf_dir)
        configure_script = os.path.join(relpath, 'configure')

        # run the configuration utility
        #rv = os.system('cd ' + conf_dir + '; /bin/sh ' + configure_script)
        print("Running libedit configuration ...")
        rv = _run_cmd('cd ' + conf_dir + '; /bin/sh ' + configure_script)
        if rv != 0:
            raise Exception("Failed configuration")

        # grab the settings
        config = {}
        parse_config_h(conf_dir, config)
        parse_autoconf(conf_dir, config)
        
        # generate the headers
        src_dir = os.path.join(conf_dir, 'src')
        rv = os.system('cd ' + src_dir + '; make vi.h emacs.h common.h fcns.h help.h func.h')
        if rv != 0:
            raise Exception("Failed header build")

        # these are based on detection
        if 'HAVE_STRLCPY' not in config:
            ext.sources.append(os.path.join('libedit', 'src', 'strlcpy.c'))
        if 'HAVE_STRLCAT' not in config:
            ext.sources.append(os.path.join('libedit', 'src', 'strlcat.c'))
        if 'HAVE_VIS' not in config:
            ext.sources.append(os.path.join('libedit', 'src', 'vis.c'))
        if 'HAVE_UNVIS' not in config:
            ext.sources.append(os.path.join('libedit', 'src', 'unvis.c'))

        # add an include dir for config.h
        ext.include_dirs.append(conf_dir)
        ext.include_dirs.append(src_dir)

        # add any needed libraries found in the built-in configuration
        ext.libraries += config['LIBS'].replace('-l', '').split()

        # build as normal
        super().build_extension(ext)
