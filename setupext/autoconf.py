"""
Support to integrate autoconf's configure support to check for system
feature availability before generating a module.
"""

import sys
import os
import tempfile
from distutils.command.build_ext import build_ext

def parse_config_h(basedir):
    """Parse the autoconf generated config.h file into a dict"""
    config_h = {}
    ch = open(os.path.join(basedir, 'config.h'))
    for line in ch.readlines():
        if line.startswith('#define'):
            parts = line.split()
            #print("config.h: " + str(parts))
            if len(parts) > 2:
                config_h[parts[1]] = parts[2].replace('"', '')
            else:
                config_h[parts[1]] = None
    ch.close()
    return config_h

def _run_cmd(cmd, tmpfile=tempfile.NamedTemporaryFile()):
    """Run a system command, putting the output into a tmp file
    Return the system exit value
    """
    if tmpfile:
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

        self.config_h = parse_config_h(self.check_dir)

    def get_libraries(self):
        """Figure out what sort of system libraries are available"""
        if 'LINE_EDITOR_LIBS' not in self.config_h:
            return []
        if self.config_h['LINE_EDITOR_LIBS'] is None:
            return []
        return self.config_h['LINE_EDITOR_LIBS'].replace('-l', '').replace('"', '').split()

    def use_builtin_libedit(self):
        """Decide if the system lib is adequate or if we need to build it in"""
        if self.force_builtin_libedit:
            return True
        if 'LINE_EDITOR' not in self.config_h:
            return True
        if self.config_h['LINE_EDITOR'] is None:
            return True
        if self.config_h['LINE_EDITOR'] != "libedit":
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
        config_h = parse_config_h(conf_dir)

        # generate the headers
        src_dir = os.path.join(conf_dir, 'src')
        rv = os.system('cd ' + src_dir + '; make vi.h emacs.h common.h fcns.h help.h func.h')
        if rv != 0:
            raise Exception("Failed header build")

        # these are based on detection
        if 'HAVE_STRLCPY' not in config_h:
            ext.sources.append(os.path.join('libedit', 'src', 'strlcpy.c'))
        if 'HAVE_STRLCAT' not in config_h:
            ext.sources.append(os.path.join('libedit', 'src', 'strlcat.c'))
        if 'HAVE_VIS' not in config_h:
            ext.sources.append(os.path.join('libedit', 'src', 'vis.c'))
        if 'HAVE_UNVIS' not in config_h:
            ext.sources.append(os.path.join('libedit', 'src', 'unvis.c'))

        # add an include dir for config.h
        ext.include_dirs.append(conf_dir)
        ext.include_dirs.append(src_dir)

        # build as normal
        super().build_extension(ext)
