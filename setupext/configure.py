#!/usr/bin/python3
#
#  Tools for emulating a bit of autoconf/configure
#

import sys
import os
import sysconfig
import tempfile
import shutil
import subprocess
import logging

from pprint import PrettyPrinter

from distutils.errors import *
from distutils.ccompiler import new_compiler
from distutils.sysconfig import customize_compiler

pp = PrettyPrinter(indent=4)

#
#  It turns out that older subprocess modules did not have the 'run'
#  function.  So, in effect, this is a backport of the run routine
#  which will work in older systems.  I'm modifying the package so that
#  calls elsewhere to subprocess.run() don't choke.
#
if not hasattr(subprocess, 'run'):
    class CompletedProcess(object):
        def __init__(self, args, retcode, stdout, stderr):
            self.args = args
            self.retcode = retcode
            self.stdout = stdout
            self.stderr = stderr
    
    def run(*popenargs, input=None, timeout=None, check=False, **kwargs):
        if input is not None:
            if 'stdin' in kwargs:
                raise ValueError('stdin and input arguments may not both be used.')
            kwargs['stdin'] = PIPE

        with subprocess.Popen(*popenargs, **kwargs) as process:
            try:
                stdout, stderr = process.communicate(input, timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                raise subprocess.TimeoutExpired(process.args, timeout,
                                                output=stdout, stderr=stderr)
            except:
                process.kill()
                process.wait()
                raise
            retcode = process.poll()
            if check and retcode:
                raise subprocess.CalledProcessError(retcode, process.args,
                                                    output=stdout+stderr)
        return CompletedProcess(process.args, retcode, stdout, stderr)

    # basically hack it in
    subprocess.run = run


from distutils import log

class ConfigureError(Exception):
    """Something in the configuration is not right."""
    pass

class Configure(object):
    """Base class for common support aspects of the configuration process."""

    cache = {}
    config = {}
    macros = []         # list of tuples (MACRO, value)
    includes = []
    include_dirs = []
    libraries = []
    
    def __init__(self, name='hostconf', compiler=None, tmpdir=None,
                 verbose=0, dry_run=0, debug=False):

        self.name = name
        self.debug = debug

        if tmpdir is None:
            self.tdir = tempfile.mkdtemp(prefix=name+'_')
        else:
            self.tdir = os.path.join(tmpdir, name)
            os.makedirs(self.tdir)

        # create a log file
        self.log = open(os.path.join(self.tdir, 'config_'+name+'.log'), 'w')

        # initialize our  indexer
        self.conf_idx = 0

        # None - init, False - during, True - Done
        self._checked_std = None

        # create the compiler infra
        self.compiler = compiler
        if self.compiler is None:
            self.compiler = new_compiler(verbose=verbose, dry_run=dry_run)
            customize_compiler(self.compiler)

        # add the Python stuff
        self.compiler.include_dirs += [sysconfig.get_config_var('INCLUDEPY')]

        #log.set_threshold(log.WARN)
        
        # hook in my spawner
        self._spawn = self.compiler.spawn
        self.compiler.spawn = self.spawn

    def __del__(self):
        if self.log:
            self.log.close()
        
        if not self.debug:
            shutil.rmtree(self.tdir)

    def dump(self):
        print("Configure.config:")
        pp.pprint(self.config)
        print("Configure.cache:")
        pp.pprint(self.cache)
        print("Configure.macros:")
        pp.pprint(self.macros)
        print("Configure.includes:")
        pp.pprint(self.includes)
        print("Configure.include_dirs:")
        pp.pprint(self.include_dirs)
        print("Configure.libraries:")
        pp.pprint(self.libraries)


    @staticmethod
    def _cache_tag(prefix, tag):
        """Create a cache tag name"""
        tag = tag.replace('/', '_')
        tag = tag.replace('.','_')
        return prefix + tag
    
    @staticmethod
    def _config_tag(prefix, tag):
        """Create a config tag name"""
        tag = tag.replace('.', '_')
        tag = tag.replace('/', '_')
        return prefix + tag.upper()


    def generate_config_log(self, config_log):
        """Somewhat puke out a similar log file to the config.log"""

        fd = open(config_log, 'w')

        fd.write('## ---------------- ##\n')
        fd.write('## Cache variables. ##\n')
        fd.write('## ---------------- ##\n')
        fd.write('\n')

        for t in sorted(self.cache.keys()):
            fd.write('{}={}\n'.format(t,self.cache[t]))

        fd.write('\n')
        fd.write('## ----------------- ##\n')
        fd.write('## Output variables. ##\n')
        fd.write('## ----------------- ##\n')
        fd.write('\n')

        fd.write("LIBS='{}'\n".format( ' -l'.join(self.libraries)))

        fd.write('\n')
        fd.write('## ----------- ##\n')
        fd.write('## confdefs.h. ##\n')
        fd.write('## ----------- ##\n')
        fd.write('\n')

        for m,v in self.macros:
            if v is None:
                v = 1
            fd.write('#define {} {}\n'.format(m,v))

        # done
        fd.close()
        
    def generate_config_h(self, config_h, config_h_in):
        """generate a config.h file based on the config.h.in template"""

        print("Creating {} from {} ...".format(config_h, config_h_in))
        
        # grab the files
        fdin = open(config_h_in, 'r')
        fd   = open(config_h, 'w')

        # iterate through the file
        for line in fdin.readlines():

            # migrate uninteresting stuff 
            if not line.startswith('#'):
                fd.write(line)
                continue

            # handle uninteresting cpp tokens
            if 'undef' not in line:
                fd.write(line)
                continue

            # chop it up
            parts = line.split()
            if parts[0] == '#' and parts[1] == 'undef':
                pptag = ''.join( parts[:1])
                tag = parts[2]
            else:
                pptag = parts[0]
                tag = parts[1]

            # handle easy undefs
            if tag in self.config:
                fd.write('#define {} 1\n'.format(tag))
            else:
                fd.write('/* ' + pptag + ' ' + tag + ' */\n')
            continue

        # mop up
        fdin.close()
        fd.close()

    def spawn(self, cmd_args):

        # run it as a subprocess to collect the output
        try:
            self.log.write(' '.join(cmd_args) + os.linesep)
            rv = subprocess.run(cmd_args,
                                timeout=5,
                                check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        except subprocess.TimeoutExpired as te_err:
            self.log.write(str(te_err))
            raise DistutilsExecError("command %r timed-out." % cmd_args)
        except subprocess.CalledProcessError as cp_err:
            self.log.write(str(cp_err))
            raise DistutilsExecError(cp_err)

        # success
        return

    def _conftest_file(self,
                       pre_main=None, main=None, add_config=False, macros=None,
                       header=None, includes=None, include_dirs=None):

        if includes is None:
            includes = []
        if include_dirs is None:
            include_dirs = []
        if macros is None:
            macros = []

        # need to make these atomic, just in case parallel stuff
        curid = self.conf_idx
        self.conf_idx += 1
        fname = 'conftest_{:03d}'.format(curid)

        # create the file
        fname = os.path.join(self.tdir, fname + '.c')

        # eventually, get the HAVE_* stuff
        conftext = []

        # setup the defs
        if add_config:
            conftext += ['#define {} {}'.format(t,v) for t,v in self.macros]
        conftext += ['#define {} {}'.format(t,v) for t,v in macros]
        
        # setup the headers
        if add_config:
            conftext += ['#include "%s"' % incl for incl in self.includes]
        conftext += ['#include "%s"' % incl for incl in includes]

        # put the main header after the others
        if header is not None:
            conftext += ['#include "%s"' % header]

        # add in the precode
        if pre_main is not None:
            conftext += pre_main
            
        # setup the body
        conftext += ['int main(void) {']

        # add in the main code
        if main is not None:
            conftext += main

        # close the body
        conftext += [
            '    return 0;',
            '}'
        ]

        # create and fill the file
        #with os.fdopen(fd, "w") as f:
        with open(fname, "w") as f:
            f.write(os.linesep.join(conftext))

        # just pass back the relative name
        return fname

    def package_info(self, name, tarname, version, bugreport=None, url=None):
        self.config['PACKAGE_NAME'] = name
        self.config['PACKAGE_TARNAME'] = tarname
        self.config['PACKAGE_VERSION'] = version
        self.config['PACKAGE_STRING'] = ' '.join([name, version])
        self.config['PACKAGE_BUGREPORT'] = bugreport or ''
        self.config['PACKAGE_URL'] = url or ''
    
    def check_std(self):
        """Run a set of very basic checks on the most common items."""

        # mark that we are "in" check_std
        self._checked_std = False


        # check ANSI headers
        oks = self.check_headers([
            'stdlib.h', 'stdarg.h', 'string.h', 'float.h'])
        if False not in oks:
            self.macros.append( ('STDC_HEADERS', 1) )

        # look for a set of basic headers
        self.check_headers([
            'sys/types.h', 'sys/stat.h', 'stdlib.h', 'string.h',
            'memory.h', 'strings.h', 'stdint.h', 'unistd.h'],
                           macros=self.macros
        )

        # flag that the std checks are done
        self._checked_std = True

    def check_python(self):
        """Verify that we can actually build something to bind to Python."""

        # snoop the sysconfig to pull in the relevant bits
        import sysconfig
        #SHLIBS = "-lpthread -ldl  -lutil"
        #PY_LDFLAGS = "-Wl,-Bsymbolic-functions -Wl,-z,relro"
        #OPT = "-DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes"
        #CONFINCLUDEPY = "/usr/include/python3.5m"
        #DESTLIB = "/usr/lib/python3.5"
        #BLDLIBRARY = "-lpython3.5m"
	#BLDSHARED = "x86_64-linux-gnu-gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions -Wl,-Bsymbolic-functions -Wl,-z,relro"

    def _check_tool(self, tool, tool_args=None):
        rv = None
        
        if tool_args is None:
            tool_args = ['--garbage']
        
        try:
            rv = subprocess.run([tool]+tool_args,
                                timeout=1,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        except FileNotFoundError as fnfe_err:
            # tool is not available
            return False, rv
        except PermissionError as p_err:
            # found something but it is not executable
            return False, rv
        except subprocess.TimeoutExpired as te_err:
            # ran it and it wedged
            return False, rv
        except subprocess.CalledProcessError as cp_err:
            # ran it and it failed, but got an exit code
            return True, rv

        # all good
        return True, rv

    def check_tool(self, tool, tool_args=None, verbose=True):
        """Try to locate a tool"""

        # setup the message
        if verbose:
            print("checking for '{}' tool ... ".format(tool), end='')

        # snoop it
        ok,rec = self._check_tool(tool=tool, tool_args=tool_args)

        if ok:
            if verbose:
                print(tool)
            return True

        if verbose:
            print('unavailable')
        return False
            

    def check_headers(self, headers, includes=None,
                      include_dirs=None, macros=None):
        """Equivalent to AC_CHECK_HEADERS"""
        results = []
        
        for header in headers:
            rv = self.check_header(header,
                                   includes=includes,
                                   include_dirs=include_dirs, macros=macros)
            results.append(rv)

        return results

    def check_header(self, header, includes=None,
                     include_dirs=None, macros=None):
        """Equivalent to AC_CHECK_HEADER"""

        # hook to be sure we do the std stuff first
        if not self._checked_std and self._checked_std is None:
            self.check_std()
        
        # setup the message
        print('checking for {} ... '.format(header), end='')

        # determine the tags
        cache_tag = self._cache_tag('ac_cv_header_', header)
        config_tag = self._config_tag('HAVE_', header)
        cache_loc = 'cached'
        
        # check the sysconfig
        rv = sysconfig.get_config_var(config_tag)
        if rv:
            self.macros.append( (config_tag, 1) )
            self.includes.append(header)
            self.config[config_tag] = rv
            self.cache[cache_tag] = 'yes'
            cache_loc = 'sysconfig'

        # cache check
        if cache_tag in self.cache and self.cache[cache_tag] == 'yes':
            print(self.cache[cache_tag] + ' ({})'.format(cache_loc))
            return True

        # assume the worst
        self.cache[cache_tag] = 'no'
        
        # create the conftest file
        fname = self._conftest_file(header=header,
                                    includes=includes, macros=macros)

        # try to compile it 
        try:
            objects = self.compiler.compile(
                [fname],
                include_dirs=include_dirs)
        except CompileError:
            print('no')
            return False

        # inventory
        self.macros.append( (config_tag, 1) )
        self.includes.append(header)
        self.config[config_tag] = 1

        # cache update
        self.cache[cache_tag] = 'yes'

        # done
        print('yes')
        return True

    def check_lib(self, funcname, library=None, includes=None, 
                  include_dirs=None, libraries=None, library_dirs=None):
        """Equivalent to AC_CHECK_LIB"""

        # hook to be sure we do the std stuff first
        if not self._checked_std and self._checked_std is None:
            self.check_std()

        # adjust arguments
        if includes is None:
            includes = []
        if include_dirs is None:
            include_dirs = []
        if libraries is None:
            libraries = []
        if library_dirs is None:
            library_dirs = []

        # create a local list and remove the empty string
        #  as it will screw up the cmdline
        local_libs = [x for x in libraries if x != '']

        # handle the case where we're looking in the 'standar libraries'
        if library is None:
            libmsg = 'stdlibs'
            dashl = ''
        else:
            dashl = '-l' + library
            local_libs.insert(0, library)
            libmsg = dashl
            
        print('checking for {} in {} ... '.format(funcname, libmsg), end='')

        # determine the tags
        cache_tag = self._cache_tag('ac_cv_func_', funcname)
        config_tag = self._config_tag('HAVE_', funcname)
        
        # check the sysconfig
        rv = sysconfig.get_config_var(config_tag)
        if rv:
            self.macros.append( (config_tag, 1) )
            self.config[config_tag] = rv
            self.cache[cache_tag] = 'yes'

        # cache check
        if cache_tag in self.cache and self.cache[cache_tag] == 'yes':
            print(self.cache[cache_tag] + ' (cached)')
            return True

        # assume the worst
        self.cache[cache_tag] = 'no'
        
        # create the conftest file
        fname = self._conftest_file(
            includes=includes,
            pre_main=['char {}(void);'.format(funcname)],
            main=['    {}();'.format(funcname),]
        )
        # the declaration is as it is because of -Wstrict-prototypes
        
        # try to compile it 
        try:
            objects = self.compiler.compile(
                [fname], include_dirs=include_dirs)
        except CompileError:
            print('no')
            return False

        # link it 
        try:
            self.compiler.link_executable(
                objects,
                os.path.basename(fname.replace('.c', '')),
                output_dir=os.path.dirname(fname),
                libraries=local_libs,
                library_dirs=library_dirs)
        except (LinkError, TypeError):
            print('no')
            return False

        # add the new library only if it is not there
        if library is not None and library not in self.libraries:
            self.libraries.append(library)

        # inventory
        self.config[config_tag] = 1
        if library is not None and library != '':
            lib_tag = self._config_tag('HAVE_LIB', library)
            self.config[lib_tag] = 1

        # update the cache
        self.cache[cache_tag] = 'yes'
        
        print('yes')
        return True

    def check_lib_link(self, funcname, library, includes=None,
                       include_dirs=None, libraries=None, library_dirs=None):
        """Verify which extra libraries are needed to link the given lib"""

        # need this to be a list
        if libraries is None:
            libraries = []

        # add the case where the library needs nothing
        if '' not in libraries:
            libraries.insert(0, '')

        # remember the pre-state
        save_LIBS = self.libraries

        # check each library in turn
        for testlib in libraries:

            # reset the list of libraries
            self.libraries = []

            # check the library by itself
            if self.check_lib(funcname, library, libraries=[testlib],
                              includes=includes, include_dirs=include_dirs,
                              library_dirs=library_dirs):
                return [testlib]

        # full restore
        self.libraries = save_LIBS
            
        # hmm. nothing worked
        return None
            

    def check_decl(self, decl, header, includes=None, include_dirs=None):
        """Equivalent to AC_CHECK_DECL"""

        # hook to be sure we do the std stuff first
        if not self._checked_std and self._checked_std is None:
            self.check_std()

        # setup the message
        print('checking for {} in {} ... '.format(decl, header), end='')

        # cache check
        cache_tag = self._cache_tag('ac_cv_func_', decl)
        if cache_tag in self.cache and self.cache[cache_tag] == 'yes':
            print(self.cache[cache_tag] + ' (cached)')
            return True

        # assume the worst
        self.cache[cache_tag] = 'no'

        # create the conftest file
        fname = self._conftest_file(
            header=header,
            includes=includes,
            main=[
                '#ifndef {0}'.format(decl),
                '#ifdef __cplusplus',
                '  (void) {0};'.format(decl),
                '#else',
                '  (void) {0};'.format(decl),
                '#endif',
                '#endif'
            ]
        )

        # try to compile it 
        try:
            objects = self.compiler.compile(
                [fname],
                include_dirs=include_dirs)
        except CompileError:
            print('no')
            return False

        # inventory
        tag = self._config_tag('HAVE_DECL_', decl)
        self.macros.append( (tag, 1) )
        self.config[tag] = 'yes'

        # update the cache
        self.cache[cache_tag] = 'yes'

        # done
        print('yes')
        return True

    def check_type(self, type_name, includes=None, include_dirs=None):
        """Emulate AC_CHECK_TYPES"""

        # hook to be sure we do the std stuff first
        if not self._checked_std and self._checked_std is None:
            self.check_std()

        if includes is None:
            includes = []
        if include_dirs is None:
            include_dirs = []

        # setup the message
        print('checking for {} ... '.format(type_name), end='')

        # cache check
        cache_tag = self._cache_tag('ac_cv_type_', type_name)
        if cache_tag in self.cache and self.cache[cache_tag] == 'yes':
            print(self.cache[cache_tag] + ' (cached)')
            return True

        # assume the worst
        self.cache[cache_tag] = 'no'

        # create the conftest file
        fname = self._conftest_file(
            includes=includes,
            add_config=True,
            main=[
                'if (sizeof ({}))'.format(type_name),
                '    return 0;',
            ]
        )

        # try to compile it 
        try:
            objects = self.compiler.compile(
                [fname],
                include_dirs=include_dirs)
        except CompileError:
            print('no')
            return False

        # inventory
        tag = self._config_tag('HAVE_TYPE_', type_name)
        self.macros.append( (tag, 1) )
        self.config[tag] = 'yes'

        # update the cache
        self.cache[cache_tag] = 'yes'

        # done
        print('yes')
        return True

    
    def check_member(self, type_name):
        """Emulate AC_CHECK_MEMBER"""
        pass

    def check_use_system_extensions(self):
        """Emulate AC_USE_SYSTEM_EXTENSIONS"""
        pass


    def check_header_dirent(self):
        """Emulate AC_HEADER_DIRENT"""
        return self.check_headers(['dirent.h', 'sys/ndir.h',
                                   'sys/dir.h', 'ndir.h'])

    def check_header_sys_wait(self):
        """Emulate AC_HEADER_SYS_WAIT"""
        return self.check_header('sys/wait.h', includes=['sys/types.h'])

    def check_type_signal(self):
        """Emulate AC_TYPE_SIGNAL"""
        ok = self.check_header('sys/signal.h', includes=['sys/types.h'])
        if ok:
            cache_tag = self._cache_tag('ac_cv_type_', 'signal')
            self.cache[cache_tag] = 'void'
        return ok

    #AC_C_CONST

    def check_type_pid_t(self):
        """Emulate AC_TYPE_PID_T"""
        rv = sysconfig.get_config_var('SIZEOF_PID_T')
        if rv:
            self.macros.append( ('HAVE_PID_T', rv) )
            return True
        return self.check_type('pid_t')

    def check_type_size_t(self):
        """Emulate AC_TYPE_SIZE_T"""
        rv = sysconfig.get_config_var('SIZEOF_SSIZE_T')
        if rv:
            self.macros.append( ('HAVE_SIZE_T', rv) )
            return True
        return self.check_type('size_t')

    #AC_FUNC_CLOSEDIR_VOID

    def check_func_fork(self):
        """Emulate AC_FUNC_FORK"""
        if not self.check_type_pid_t():
            return False

        rv = sysconfig.get_config_var('HAVE_FORK')
        if rv:
            self.macros.append( ('HAVE_FORK', rv) )
            self.macros.append( ('HAVE_WORKING_FORK', 1) )            

        rv = sysconfig.get_config_var('HAVE_VFORK')
        if rv:
            self.macros.append( ('HAVE_VFORK', rv) )
            self.macros.append( ('HAVE_WORKING_VFORK', 1) )

        if not self.check_header('vfork.h'):
            return False
        
        return False
        
    #AC_PROG_GCC_TRADITIONAL

    def check_func_stat(self):
        """Emulate AC_FUNC_STAT"""

        ok = self.check_header('sys/stat.h')
        
        


        
if __name__ == '__main__':
    cf = Configure(debug=True)

    rv = cf.check_lib('el_init', 'edit', libraries=[''])

    rv = cf.check_header('histedit.h')
    
    oks = cf.check_headers(['stdio.h', 'stdlib.h', 'string.h'])

    rv = cf.check_header('Python.h')

    rv = cf.check_header('Bork.h')

    rv = cf.check_decl('EL_EDITOR', 'histedit.h')

    libs = cf.check_lib_link('el_init', 'edit',
                             libraries=['', 'tinfo', 'ncurses',
                                        'curses', 'termcap'])
    if libs is None or '' in libs:
        print("libedit needs: none")
    else:
        print("libedit needs:", ' -l'.join(libs))
        cf.libraries += libs
    
    print("LIBS:", cf.libraries)
    #pp.pprint(cf.libraries)
    print("Config:")
    pp.pprint(cf.config)
