"""
Support to integrate autoconf's configure support to check for system
feature availability before generating a module.
"""

import sys
import os
import re
import tempfile

from distutils import log
from distutils.cmd import Command
from distutils.command.build import build
from distutils.command.build_clib import build_clib
from distutils.command.build_ext import build_ext
from distutils.command.build_py import build_py
from distutils.command.install_lib import install_lib

from setupext.hostconf.configure import *

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


#
# Interestingly, there is not actually so much to check.
#
# grep -R HAVE_ src/libedit/src/ src/libedit/src/  | \
#       sed -E -e 's/^.*(HAVE_\w+).*$/\1/' | sort | uniq
#
# grep -R '^#include'  src/libedit/src/ src/libedit/gen/ | \
#       sed -E -e 's/^.*:#include\s+//' -e 's/>.*$/>/' | \
#            grep '^<' | sort | uniq
#

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

    # common libs needed for libedit
    terminal_libs = ['tinfo', 'ncursesw', 'ncurses', 'curses', 'termcap']

    # static dirs
    libedit_dir = os.path.join('src', 'libedit')
    libedit_src_dir = os.path.join('src', 'libedit', 'src')

    # option support
    user_options = build.user_options + [
        ('builtin-libedit', None, "Force use of builtin libedit"),
    ]
    boolean_options = build.boolean_options + ['builtin-libedit']

    def initialize_options(self):
        super().initialize_options()
        self.builtin_libedit = None

    def finalize_options(self):
        super().finalize_options()

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
        # do we ignore it?
        if self.builtin_libedit:
            return False
        
        # setup the configurator
        ctool = Configure('conf_local', tmpdir=self.build_temp,
                          compiler=self.compiler, debug=True)
        ctool.package_info('libedit', 'libedit-20180315', '3.1')

        # will libedit even link, if so what does it need...
        exlibs = ctool.check_lib_link(
            'el_init', 'edit',
            libraries=['']+[x for x in self.terminal_libs])
        
        # nothing linked at all?
        if exlibs is None:
            return False

        # pop the 'empty' out to avoid a lingering '-l'
        if '' in exlibs:
            exlibs.remove('')

        # check for the necessary system header files
        oks = ctool.check_headers([
            'stddef.h', 'setjmp.h', 'signal.h', 'errno.h', 'sys/time.h'
        ])
        if False in oks:
            return False

        # check for python headers
        ok = ctool.check_header('Python.h')
        if not ok:
            return False

        ok = ctool.check_header('structmember.h', includes=['Python.h'])
        if not ok:
            return False

        # check for specific libedit header
        oks = ctool.check_headers(['histedit.h'])
        if False in oks:
            return False

        #print("exlibs:", exlibs)
        #print("libs:", ctool.libraries)
        
        # ok, something is there...
        for fcn in ['el_init', 'el_get', 'el_set', 'el_line', 'el_insertstr',
                    'el_gets', 'el_source', 'el_reset', 'el_end', 'tok_init',
                    'tok_end', 'history', 'history_init', 'history_end']:
            ok = ctool.check_lib(fcn, 'edit', libraries=exlibs)
            if not ok:
                return False

        #print("exlibs2:", exlibs)
        #print("libs2:", ctool.libraries)

        # check the tokens needed 
        for token in ['EL_EDITOR', 'EL_SIGNAL', 'EL_PROMPT_ESC',
                      'EL_RPROMPT_ESC', 'EL_HIST', 'EL_ADDFN',
                      'EL_BIND', 'EL_CLIENTDATA', 'EL_REFRESH',
                      'EL_GETTC', 'H_ENTER']:
            ok = ctool.check_decl(token, 'histedit.h')
            if not ok:
                return False

        #print("exlibs3:", exlibs)
        #print("libs3:", ctool.libraries)
        
        # looks good - add the extra libraries if any
        cext.libraries += ctool.libraries + exlibs

        # done
        return True

    def check_system(self, clib):
        """Run the system inspection to create config.h"""
        # setup the configurator
        ctool = Configure('conf_edit', tmpdir=self.build_temp,
                          compiler=self.compiler, debug=True)
        ctool.package_info('libedit', '3.1', '20180315')

        # early items...
        ctool.check_stdc()
        ctool.check_use_system_extensions()
        
        # check for the necessary system header files
        ctool.check_headers(['fcntl.h', 'limits.h', 'malloc.h',
                             'sys/ioctl.h', 'sys/param.h', 'sys/cdefs.h',
                             'dlfcn.h'])

        # some uncommon headers
        ctool.check_header_dirent()
        ctool.check_header_sys_wait()

        # struct dirent has memeber d_namelen
        ctool.check_member('struct dirent', 'd_namlen', includes=['dirent.h'])
        
        # figure out which terminal lib we have
        for testlib in self.terminal_libs:
            ok = ctool.check_lib('tgetent', testlib)
            if ok:
                break

        # it better have linked to something!
        if not ok:
            tlibs = [ 'lib'+x for x in self.terminal_libs ]
            raise ConfigureSystemLibraryError('tgetent', tlibs)

        # common places for ncursesw?
        ncursesw_locs = [
            os.path.sep + 'usr',
            os.path.sep + os.path.join('usr', 'local')            
        ]
        
        # check common places for 'ncursesw' dir:
        for loc in ncursesw_locs:
            tpath = os.path.join(loc, 'include', 'ncursesw')
            if os.path.isdir(tpath):
                ctool.include_dirs.insert(0, tpath)
                print("DBG: Found ncursesw dir:", tpath)
                break
        
        # check for terminal headers
        term_headers = ['ncurses.h', 'curses.h', 'termcap.h']
        oks = ctool.check_headers(term_headers, include_dirs=ctool.include_dirs)
        if True not in oks:
            raise ConfigureSystemHeaderFileError(term_headers)

        # must have termios.h
        ok = ctool.check_header('termios.h')
        if not ok:
            raise ConfigureSystemHeaderFileError(['termios.h'], 'this header:')

        # must have term.h
        ctool.check_header('term.h', include_dirs=ctool.include_dirs)

        #AC_C_CONST

        ctool.check_type_pid_t()
        ctool.check_type_size_t()
        ctool.check_type('u_int32_t')
        
        #AC_FUNC_CLOSEDIR_VOID
        
        ctool.check_func_fork()
        ctool.check_func_vfork()

        #AC_PROG_GCC_TRADITIONAL

        ctool.check_type_signal()

        ctool.check_func_lstat()
        
        # check for bsd/string.h -- mainly for linux
        ok = ctool.check_header('bsd/string.h')
        if ok:
            ctool.check_lib('strlcpy', 'bsd')

        # check a bunch of standard-ish functions
        fcns = [
            'endpwent', 'isascii', 'memchr', 'memset', 're_comp',
            'regcomp', 'strcasecmp', 'strchr', 'strcspn', 'strdup', 'strerror',
            'strrchr', 'strstr', 'strtol', 'issetugid', 'wcsdup', 'strlcpy',
            'strlcat', 'getline', 'vis', 'strvis', 'unvis', 'strunvis',
            '__secure_getenv', 'secure_getenv']
        for fcn in fcns:
            ctool.check_lib(fcn, libraries=ctool.libraries)

        # these probably should be local
        ctool.check_getpw_r__posix()
        ctool.check_getpw_r__draft()

        # debugging
        #ctool.dump()
        
        # looks good - add the extra libraries if any
        clib['libraries'] += ctool.libraries

        # locate the config template and output
        config_h = os.path.join(self.build_temp, self.libedit_dir, 'config.h')
        config_h_in = os.path.join(self.libedit_dir, 'config.h.in')
        
        # barf out the config.h file from config.h.in
        ctool.generate_config_h(config_h, config_h_in)
        ctool.generate_config_log(config_h.replace('.h','.log'))
        
        # done
        return ctool

    def configure_builtin_libedit(self, ext):

        print("Reconfiguring for builtin libedit")

        # first off, setup include paths for *our* libedit headers
        ext.include_dirs += [ self.libedit_dir ]
        
        # setup the infra for the clib build
        lib = {
            'sources': [],
            'include_dirs': [],
            'macros': [],
            'libraries': []
        }

        # setup common paths
        self.conf_dir = os.path.join(self.build_temp, self.libedit_dir)
        self.build_src_dir = os.path.join(self.conf_dir, 'src')

        # update to append the additional sources
        for srcfile in self.builtin_srcs:
            lib['sources'].append(os.path.join(self.libedit_src_dir, srcfile))

        # add these to match the new srcs
        lib['include_dirs'] += [
            self.libedit_dir,
            os.path.join(self.libedit_dir, 'gen'),
            os.path.join(self.libedit_src_dir)
        ]

        # we'll cook up a config.h
        lib['macros'] += [('HAVE_CONFIG_H', None)]
        
        # create the basic build area
        print("creating " + self.conf_dir)
        os.makedirs(self.conf_dir, exist_ok=True)

        # generate the config* files
        ctool = self.check_system(lib)

        # record any new dirs
        if ctool.include_dirs is not None:
            lib['include_dirs'] += ctool.include_dirs

        # these are based on detection
        if 'HAVE_STRLCPY' not in ctool.config:
            lib['sources'].append(
                os.path.join(self.libedit_src_dir, 'strlcpy.c'))
        if 'HAVE_STRLCAT' not in ctool.config:
            lib['sources'].append(
                os.path.join(self.libedit_src_dir, 'strlcat.c'))
        if 'HAVE_VIS' not in ctool.config:
            lib['sources'].append(
                os.path.join(self.libedit_src_dir, 'vis.c'))
        if 'HAVE_UNVIS' not in ctool.config:
            lib['sources'].append(
                os.path.join(self.libedit_src_dir, 'unvis.c'))

        # add an include dir for config.h
        lib['include_dirs'].append(self.conf_dir)

        # add any needed libraries found in the built-in configuration
        ext.libraries += [lib for lib in ctool.libraries]

        # hook-in the library build
        self.distribution.libraries += [('edit_builtin', lib)]
        
        # done
        return

    def run(self):
        # locate the extension 
        cext = self.get_editline_extension()

        # increase the log level to quiet the spew
        oldlog = log.set_threshold(log.WARN)
        
        # check for the locally installed library
        found = self.check_local_libedit(cext)

        # setup the internal build if necessary
        if not found:
            self.configure_builtin_libedit(cext)

        # restore
        log.set_threshold(oldlog)
            
        # now run the common build
        super().run()


class OptimizeBuildExt(build_ext):
    """Setup an extension which strips the extension if there are tools to
       do it."""

    # option support
    user_options = build_ext.user_options + [
        ('no-strip', None, "Omit the object stripping"),
    ]
    boolean_options = build_ext.boolean_options + ['no-strip']

    def initialize_options(self):
        super().initialize_options()
        self.no_strip = None

    def finalize_options(self):
        super().finalize_options()

        # setup the no_strip to a boolean value
        if self.no_strip is None:
            self.no_strip = False
        else:
            self.no_strip = True

    def _locate_strip_tool(self):
        # got nothing to begin with
        stripper = None

        # pie-in-the-sky hope that it will eventually show up
        if 'strip' in self.compiler.executables:
            stripper = self.compiler.executables['strip']
            if stripper is not None:
                return stripper

        # setup the configurator
        ctool = Configure('conf_buildext', tmpdir=self.build_temp,
                          compiler=self.compiler, debug=True)
        ctool.package_info('libedit', 'libedit-20180321', '3.1')

        # ok, let's see if we can hack one together
        cc = self.compiler.compiler_so[0]

        # do we have some sort of GCC?
        if 'gcc' in cc or 'g++' in cc:
            stripper = cc.replace('gcc', 'strip').replace('g++', 'strip')
            ok = ctool.check_tool(stripper, verbose=False)
            if ok:
                return stripper

        # generic 'cc'
        if cc == 'cc':
            ok = ctool.check_tool('strip', verbose=False)
            if ok:
                return 'strip'

        # nope
        return None
    
    def build_extension(self, ext):
        """Strip the extension"""
        
        # do everything as normal
        super().build_extension(ext)

        # did we get specifically called off
        if self.no_strip:
            return

        # debug builds we leave alone
        if self.debug:
            return

        # make sure we have some sort of compiler
        if self.compiler is None:
            return

        # not sure windoze does this
        if self.compiler.compiler_type is not 'unix':
            return

        # get the tool
        strip = self._locate_strip_tool()
        if strip is None:
            return

        # locate the compiled extension
        ext_path = self.get_ext_fullpath(ext.name)

        # collect the initial size
        pre_stat = os.stat(ext_path)

        # run it basically
        try:
            print("stripping", ext_path)
            self.compiler.spawn([strip, ext_path])
        except DistutilsExecError as msg:
            raise CompileError(msg)

        # after the tool ran
        post_stat = os.stat(ext_path)

        # check on savings
        delta = (pre_stat.st_size - post_stat.st_size) // 1024

        # update user
        print("stripping saved {:d} KB.".format(delta))

    def get_libraries(self, ext):
        libs = super().get_libraries(ext)

        # problem: compiler puts custom libs AFTER system libs in the link
        #          command.  This is incorrect and leaves dangling symbols.
        #          SHOULD be fixed in the build_ext run initial code to
        #          *prepend* not *append* CLIBs.

        # well, hack around it...
        print("Note: distutils sets-up syslibs before clibs... correcting")

        # save the clib names
        clib_libs = self.libraries

        # back out the improperly appended libs
        self.libraries = []
        self.compiler.set_libraries(self.libraries)

        # re-order them to make sure the clibs are FIRST
        libs = clib_libs + libs

        # done
        return libs

