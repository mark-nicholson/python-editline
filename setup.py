#!/usr/bin/env python3

import sys, os
from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext

class ConfigureBuildExt(build_ext):
    
    def run(self):
        print("CBE.run()")
        super().run()

    def parse_config_h(self, basedir):
        ch = open(os.path.join(basedir, 'config.h'))
        self.config_h = {}
        for line in ch.readlines():
            if line.startswith('#define'):
                parts = line.split()
                print("config.h: " + str(parts))
                if len(parts) > 2:
                    self.config_h[parts[1]] = parts[2]
                else:
                    self.config_h[parts[1]] = 1
        ch.close()
        
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
        rv = os.system('cd ' + conf_dir + '; /bin/sh ' + configure_script)
        if rv != 0:
            raise Exception("Failed configuration");

        self.parse_config_h(conf_dir)

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

#
# These are the basic build parameters
#
sources = [ os.path.join('src','_editline.c') ]
include_dirs = []
libraries = [ 'edit' ]
define_macros = []
cmdclass = {
    'build_ext': build_ext
}

# built-in libedit needed?
if False:
#if True:
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

    include_dirs += [ os.path.join('libedit', 'src'), 'libedit' ]
    define_macros = [ ('HAVE_CONFIG_H', None) ]
    cmdclass['build_ext'] = ConfigureBuildExt


# termcap is needed on OpenBSD.
if sys.platform in [ 'openbsd6' ]:
    libraries.append( 'termcap' )
elif sys.platform in [ 'sunos5' ]:
    libraries.append( 'ncurses' )
elif sys.platform in [ 'linux' ]:
    libraries.append( 'tinfo' )

# add additional library quirks

editline_module = Extension(
    '_editline',
    sources = sources,
    libraries = libraries,
    include_dirs = include_dirs
)


setup(name = '_editline',
      version = '1.0',
      description = 'Python modules to support libedit directly',
      ext_modules = [editline_module],

      py_modules = [ 'editline', 'lineeditor' ],

      cmdclass = cmdclass,

      url='http://sites.nicholnet.com',
      author='Mark Nicholson',
      author_email='nicholson.mark at gmail dot com')
