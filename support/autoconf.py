
import sys, os
import tempfile
from distutils.command.build_ext import build_ext

def parse_config_h(basedir):
    config_h = {}
    ch = open(os.path.join(basedir, 'config.h'))
    for line in ch.readlines():
        if line.startswith('#define'):
            parts = line.split()
            #print("config.h: " + str(parts))
            if len(parts) > 2:
                config_h[parts[1]] = parts[2]
            else:
                config_h[parts[1]] = None
    ch.close()
    return config_h

def _run_cmd(cmd, tmpfile=tempfile.NamedTemporaryFile()):
    if tmpfile:
        cmd += " > {}".format(tmpfile.name)
    rv = os.system(cmd)
    if tmpfile:
        tmpfile.close()
    return rv
        

class GeneralConfig(object):

    def __init__(self):
        self.check_dir = 'check'
        self.configure_script = 'configure'
        self.force_builtin_libedit = False

        for i,arg in enumerate(sys.argv):
            if arg == '--builtin-libedit':
                self.force_builtin_libedit = True
                del(sys.argv[i])

        self.run_check()

    def run_check(self):
        # run the configuration utility
        print("Running system inspection ...")
        rv = _run_cmd('cd ' + self.check_dir + '; /bin/sh ' + self.configure_script)
        if rv != 0:
            raise Exception("Failed configuration ({})".format(rv));

        self.config_h = parse_config_h(self.check_dir)

    def get_libraries(self):
        if 'LINE_EDITOR_LIBS' not in self.config_h:
            return []
        if self.config_h['LINE_EDITOR_LIBS'] is None:
            return []
        return self.config_h['LINE_EDITOR_LIBS'].replace('-l', '').replace('"', '').split()

    def use_builtin_libedit(self):
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
    
    def run(self):
        print("CBE.run()")
        super().run()

    def build_extension(self, ext):
        print("CBE.build_extension()");
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
            raise Exception("Failed configuration");

        # grab the settings
        self.config_h = parse_config_h(conf_dir)

        # generate the headers
        src_dir = os.path.join(conf_dir, 'src')
        rv = os.system('cd ' + src_dir + '; make vi.h emacs.h common.h fcns.h help.h func.h')
        if rv != 0:
            raise Exception("Failed header build");

        # these are based on detection
        if 'HAVE_STRLCPY' not in self.config_h:
            ext.sources.append( os.path.join('libedit', 'src', 'strlcpy.c') )
        if 'HAVE_STRLCAT' not in self.config_h:
            ext.sources.append( os.path.join('libedit', 'src', 'strlcat.c') )
        if 'HAVE_VIS' not in self.config_h:
            ext.sources.append( os.path.join('libedit', 'src', 'vis.c') )
        if 'HAVE_UNVIS' not in self.config_h:
            ext.sources.append( os.path.join('libedit', 'src', 'unvis.c') )
        
        # add an include dir for config.h
        ext.include_dirs.append(conf_dir)
        ext.include_dirs.append(src_dir)

        # build as normal
        super().build_extension(ext)

#CC   --mode=compile gcc -DHAVE_CONFIG_H -I. -I../../libedit/src -I..     -g -O2 -MT filecomplete.lo -MD -MP -MF .deps/filecomplete.Tpo -c -o filecomplete.lo ../../libedit/src/filecomplete.c
