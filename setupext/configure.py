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
            self.returncode = retcode
            self.stdout = stdout
            self.stderr = stderr

        def check_returncode(self):
            if self.returncode:
                raise CalledProcessError(self.returncode, self.args,
                                         self.stdout, self.stderr)
                
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
        self._checked_stdc = None

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
            pptag,tag = line.rsplit(maxsplit=1)
            
            # handle easy undefs
            if tag not in self.config:
                fd.write('/* ' + pptag + ' ' + tag + ' */\n')
                continue

            # grab the value
            value = self.config[tag]

            # change undef -> define without modifying whitespace
            pptag = pptag.replace('undef', 'define')

            # finish it up
            fd.write('{} {} {}'.format(pptag, tag, value) + os.linesep)

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
            rv.check_returncode()
        except subprocess.TimeoutExpired as te_err:
            self.log.write("process timeout ({:d}s) error".format(te_err.timeout) + os.linesep)
            self.log.write("stdout output:" + os.linesep)
            self.log.write(str(te_err.stdout))
            self.log.write("stderr output:" + os.linesep)
            self.log.write(str(te_err.stderr))
            raise DistutilsExecError("command %r timed-out." % cmd_args)

        except subprocess.CalledProcessError as cp_err:
            self.log.write("process error: ({:d})".format(cp_err.returncode) + os.linesep)
            if cp_err.stdout != b'':
                errstrs = cp_err.stdout.decode('utf-8').split('\n')
                self.log.write("stdout output:" + os.linesep)
                for es in errstrs:
                    self.log.write(es + os.linesep)
            if cp_err.stderr != b'':
                errstrs = cp_err.stderr.decode('utf-8').split('\n')
                self.log.write("stderr output:" + os.linesep)
                for es in errstrs:
                    self.log.write(es + os.linesep)
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

        # eventually, get the have_* stuff
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

        # log it
        for line in conftext:
            self.log.write('| ' + line + os.linesep)

        # create and fill the file
        #with os.fdopen(fd, "w") as f:
        with open(fname, "w") as f:
            f.write(os.linesep.join(conftext))

        # just pass back the relative name
        return fname

    def package_info(self, name, version, release, bugreport=None, url=None):
        self.add_macro('PACKAGE_NAME', name, quoted=True)
        self.add_macro('PACKAGE_TARNAME', '-'.join([name, release]), quoted=True)
        self.add_macro('PACKAGE_VERSION', version, quoted=True)
        self.add_macro('PACKAGE_STRING', ' '.join([name, version]), quoted=True)
        self.add_macro('PACKAGE_BUGREPORT', bugreport or '', quoted=True)
        self.add_macro('PACKAGE_URL', url or '', quoted=True)
        self.add_macro('PACKAGE', '-'.join([name, release]), quoted=True)
        self.add_macro('VERSION', version, quoted=True)

        # this is not really valid, but should be there
        self.config['LT_OBJDIR'] = '".libs/"'

    def check_msg(self, item, item_in=None, extra=None):
        # format the banner
        msg = "checking for " + item
        if item_in is not None:
            msg = msg + " in " + item_in
        if extra is not None:
            msg += ' ' + extra
        msg += " ... "

        # log it
        self.log.write(os.linesep)
        self.log.write('#' * 60 + os.linesep)
        self.log.write(msg + os.linesep)
        self.log.write('#' * len(msg) + os.linesep)

        # print to the terminal without a line ending
        print(msg, end='')

    def check_msg_result(self, msg):
        logmsg = "result: " + msg
        self.log.write(os.linesep)
        self.log.write('#' * len(logmsg) + os.linesep)
        self.log.write(logmsg + os.linesep)
        self.log.write('#' * 60 + os.linesep * 2)

        print(msg)

    def add_macro(self, macro, macro_value, config_value=None, quoted=False):
        if quoted:
            macro_value = '"' + macro_value + '"'
        self.macros.append( (macro, macro_value) )
        if config_value is None:
            config_value = macro_value
        else:
            if quoted:
                config_value = '"' + config_value + '"'
        self.config[macro] = config_value
        
    def check_stdc(self):
        """run a set of very basic checks on the most common items."""

        # mark that we are "in" check_stdc
        self._checked_stdc = False


        # check ansi headers
        oks = self.check_headers([
            'stdlib.h', 'stdarg.h', 'string.h', 'float.h'])
        if False not in oks:
            self.add_macro('STDC_HEADERS', 1)

        pre_main = self._get_stdc_header_defs()
            
        # look for a set of basic headers
        self.check_headers([
            'sys/types.h', 'sys/stat.h', 'stdlib.h', 'string.h',
            'memory.h', 'strings.h', 'inttypes.h', 'stdint.h', 'unistd.h'],
            macros=self.macros, pre_main=pre_main
        )

        # flag that the std checks are done
        self._checked_stdc = True

    def _get_stdc_header_defs(self):
        pre_main_text = '''
        #include <stdio.h>
        #ifdef HAVE_SYS_TYPES_H
        # include <sys/types.h>
        #endif
        #ifdef HAVE_SYS_STAT_H
        # include <sys/stat.h>
        #endif
        #ifdef STDC_HEADERS
        # include <stdlib.h>
        # include <stddef.h>
        #else
        # ifdef HAVE_STDLIB_H
        #  include <stdlib.h>
        # endif
        #endif
        #ifdef HAVE_STRING_H
        # if !defined STDC_HEADERS && defined HAVE_MEMORY_H
        #  include <memory.h>
        # endif
        # include <string.h>
        #endif
        #ifdef HAVE_STRINGS_H
        # include <strings.h>
        #endif
        #ifdef HAVE_INTTYPES_H
        # include <inttypes.h>
        #endif
        #ifdef HAVE_STDINT_H
        # include <stdint.h>
        #endif
        #ifdef HAVE_UNISTD_H
        # include <unistd.h>
        #endif
        '''
        pre_main = []
        for line in pre_main_text.split(os.linesep):
            pre_main.append(line.strip())
        return pre_main

    def _check_compile(self, main=None, pre_main=None,
                       macros=None, includes=None, include_dirs=None):
        
        # just setup the file
        ctfname = self._conftest_file(
            macros=macros,
            includes=includes,
            pre_main=pre_main,
            main=main
        )
        
        # try to compile it 
        try:
            objects = self.compiler.compile(
                [ctfname],
                include_dirs=include_dirs
                #output_dir=os.path.dirname(ctfname)
            )
        except CompileError:
            return False

        return True
        
    def _check_run(self, main=None, pre_main=None,
                   macros=None, includes=None, include_dirs=None,
                   library_dirs=None):
        
        # just setup the file
        ctfname = self._conftest_file(
            macros=macros,
            includes=includes,
            pre_main=pre_main,
            main=main
        )
        
        # try to compile it 
        try:
            objects = self.compiler.compile(
                [ctfname],
                include_dirs=include_dirs
                #output_dir=os.path.dirname(ctfname),
                )
        except CompileError:
            return False

        # test file
        exe_file = os.path.basename(ctfname.replace('.c', ''))
        
        # now try to link it...
        try:
            self.compiler.link_executable(
                objects,
                exe_file,
                output_dir=os.path.dirname(ctfname),
                library_dirs=library_dirs)
        except LinkError:
            return False

        # run it 
        try:
            self.spawn([os.path.join(self.tdir,exe_file)])
        except DistutilsExecError as dee:
            return False

        # success...
        return True
        
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
            self.check_msg(tool, extra="tool")

        # snoop it
        ok,rec = self._check_tool(tool=tool, tool_args=tool_args)

        if ok:
            if verbose:
                self.check_msg_result(tool)
            return True

        if verbose:
            self.check_msg_result('unavailable')
        return False
            

    def check_headers(self, headers, includes=None,
                      include_dirs=None, macros=None, pre_main=None):
        """Equivalent to AC_CHECK_HEADERS"""
        results = []
        
        for header in headers:
            rv = self.check_header(header,
                                   includes=includes,
                                   include_dirs=include_dirs, macros=macros,
                                   pre_main=pre_main)
            results.append(rv)

        return results

    def check_header(self, header, includes=None,
                     include_dirs=None, macros=None, pre_main=None):
        """Equivalent to AC_CHECK_HEADER"""

        # hook to be sure we do the std stuff first
        if not self._checked_stdc and self._checked_stdc is None:
            self.check_stdc()
        
        # setup the message
        self.check_msg(header)

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
            self.check_msg_result(
                self.cache[cache_tag] + ' ({})'.format(cache_loc)
            )
            return True

        # assume the worst
        self.cache[cache_tag] = 'no'
        
        # create the conftest file
        fname = self._conftest_file(header=header,
                                    includes=includes, macros=macros,
                                    pre_main=pre_main)

        # try to compile it 
        try:
            objects = self.compiler.compile(
                [fname],
                include_dirs=include_dirs
                #output_dir=os.path.dirname(fname)
            )
        except CompileError:
            self.check_msg_result('no')
            return False

        # inventory
        self.macros.append( (config_tag, 1) )
        self.includes.append(header)
        self.config[config_tag] = 1

        # cache update
        self.cache[cache_tag] = 'yes'

        # done
        self.check_msg_result('yes')
        return True

    def check_lib(self, funcname, library=None, includes=None, 
                  include_dirs=None, libraries=None, library_dirs=None):
        """Equivalent to AC_CHECK_LIB"""

        # hook to be sure we do the std stuff first
        if not self._checked_stdc and self._checked_stdc is None:
            self.check_stdc()

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
            
        self.check_msg(funcname, item_in=libmsg)

        # determine the tags
        cache_tag = self._cache_tag('ac_cv_func_', funcname)
        config_tag = self._config_tag('HAVE_', funcname)
        
        # check the sysconfig
        rv = sysconfig.get_config_var(config_tag)
        if rv:
            self.add_macro(config_tag, 1, rv)
            self.cache[cache_tag] = 'yes'

        # cache check
        if cache_tag in self.cache and self.cache[cache_tag] == 'yes':
            self.check_msg_result(self.cache[cache_tag] + ' (cached)')
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
                [fname],
                include_dirs=include_dirs
                #output_dir=os.path.dirname(fname)
            )
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
            self.check_msg_result('no')
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
        
        self.check_msg_result('yes')
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
            

    def check_decl(self, decl, header, includes=None, include_dirs=None, main=None):
        """Equivalent to AC_CHECK_DECL"""

        # hook to be sure we do the std stuff first
        if not self._checked_stdc and self._checked_stdc is None:
            self.check_stdc()

        # setup the message
        self.check_msg(decl, header)

        # cache check
        cache_tag = self._cache_tag('ac_cv_func_', decl)
        if cache_tag in self.cache and self.cache[cache_tag] == 'yes':
            self.check_msg_result(self.cache[cache_tag] + ' (cached)')
            return True

        # assume the worst
        self.cache[cache_tag] = 'no'

        if main is None:
            main = [
                '#ifndef {0}'.format(decl),
                '#ifdef __cplusplus',
                '  (void) {0};'.format(decl),
                '#else',
                '  (void) {0};'.format(decl),
                '#endif',
                '#endif'
            ]
            

        # create the conftest file
        fname = self._conftest_file(
            header=header,
            includes=includes,
            main=main
        )

        # try to compile it 
        try:
            objects = self.compiler.compile(
                [fname],
                include_dirs=include_dirs
                #output_dir=os.path.dirname(fname)
            )
        except CompileError:
            self.check_msg_result('no')
            return False

        # inventory
        tag = self._config_tag('HAVE_DECL_', decl)
        self.add_macro(tag, 1)

        # update the cache
        self.cache[cache_tag] = 'yes'

        # done
        self.check_msg_result('yes')
        return True

    def check_type(self, type_name, includes=None, include_dirs=None):
        """Emulate AC_CHECK_TYPES"""

        # hook to be sure we do the std stuff first
        if not self._checked_stdc and self._checked_stdc is None:
            self.check_stdc()

        if includes is None:
            includes = []
        if include_dirs is None:
            include_dirs = []

        # setup the message
        self.check_msg(type_name)

        # cache check
        cache_tag = self._cache_tag('ac_cv_type_', type_name)
        if cache_tag in self.cache and self.cache[cache_tag] == 'yes':
            self.check_msg_result(self.cache[cache_tag] + ' (cached)')
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
                include_dirs=include_dirs
                #output_dir=os.path.dirname(fname)
            )
        except CompileError:
            self.check_msg_result('no')
            return False

        # inventory
        tag = self._config_tag('HAVE_', type_name)
        self.add_macro(tag, 1)
        #self.macros.append( (tag, 1) )
        #self.config[tag] = 1

        # update the cache
        self.cache[cache_tag] = 'yes'

        # done
        self.check_msg_result('yes')
        return True

    
    def check_member(self, type_name):
        """Emulate AC_CHECK_MEMBER"""
        pass

    def check_use_system_extensions(self):
        """Emulate AC_USE_SYSTEM_EXTENSIONS"""

        # setup the message
        self.check_msg('system extensions')

        pre_main = self._get_stdc_header_defs()

        ok = self._check_compile(
            macros=self.macros,
            pre_main=['#define __EXTENSIONS__ 1']+pre_main
        )
        if ok:
            self.check_msg_result('yes')
            self.add_macro('__EXTENSIONS__', 1)
            self.add_macro('_ALL_SOURCE', 1)
            self.add_macro('_GNU_SOURCE', 1)
            self.add_macro('_POSIX_PTHREAD_SEMANTICS', 1)
            self.add_macro('_TANDEM_SOURCE', 1)
        else:
            self.check_msg_result('no')

        return ok



    def check_header_dirent(self):
        """Emulate AC_HEADER_DIRENT"""
        for header in ['dirent.h', 'sys/ndir.h', 'sys/dir.h', 'ndir.h']:
            ok = self.check_decl('DIR', header,
                                 includes=['sys/types.h'],
                                 main=[
                                     'if ((DIR *) 0) {',
                                     '   return 0;',
                                     '}'
                                 ]
            )
            if ok:
                tag = self._config_tag('HAVE_', header)
                self.add_macro(tag, 1)
                return True
        return False

    def check_header_sys_wait(self):
        """Emulate AC_HEADER_SYS_WAIT"""
        return self.check_header('sys/wait.h', includes=['sys/types.h'])

    def check_type_signal(self):
        """Emulate AC_TYPE_SIGNAL"""
        cache_tag = self._cache_tag('ac_cv_type_', 'signal')

        # check the sysconfig
        rv = sysconfig.get_config_var('RETSIGTYPE')
        if rv:
            self.cache[cache_tag] = 'void'
            self.add_macro('RETSIGTYPE', 'void')
            return True

        # estimate it 
        ok = self.check_header('sys/signal.h', includes=['sys/types.h'])
        if ok:
            self.cache[cache_tag] = 'void'
            self.add_macro('RETSIGTYPE', 'void')
        return ok

    #AC_C_CONST

    def check_type_pid_t(self):
        """Emulate AC_TYPE_PID_T"""
        rv = sysconfig.get_config_var('SIZEOF_PID_T')
        if rv:
            self.add_macro('HAVE_PID_T', rv)
            return True
        return self.check_type('pid_t')

    def check_type_size_t(self):
        """Emulate AC_TYPE_SIZE_T"""
        rv = sysconfig.get_config_var('SIZEOF_SSIZE_T')
        if rv:
            self.add_macro('HAVE_SIZE_T', rv)
            return True
        return self.check_type('size_t')

    #AC_FUNC_CLOSEDIR_VOID

    def check_func_fork(self, fcn='fork'):
        """Emulate AC_FUNC_FORK"""
        rv = False

        # got to have this to work
        if not self.check_type_pid_t():
            return rv

        self.check_msg(fcn)

        # setup the tags
        HF = self._config_tag('HAVE_', fcn)
        chf = self._cache_tag('ac_cv_func_', fcn)
        HWF = self._config_tag('HAVE_WORKING_', fcn)
        chwf = chf + '_working'

        # python check this already?
        ok = sysconfig.get_config_var(HF)
        if ok:
            self.add_macro(HF, 1)
            self.cache[chf] = 'yes'
            rv = True
        else:
            # ok, see if it is there
            ok = self.check_lib(fcn)
            if ok:
                self.add_macro(HF, 1)
                self.cache[chf] = 'yes'
                rv = True

        # check for it working...
        ok = sysconfig.get_config_var(HWF)
        if ok:
            self.add_macro(HWF, 1)
            self.cache[chwf] = 'yes'
            rv = True
        else:
            # assuming this for now...
            self.add_macro(HWF, 1)
            self.cache[chwf] = 'yes'
            rv = True

        # update banner
        if rv:
            self.check_msg_result('yes')
        else:
            self.check_msg_result('no')

        return rv

    def check_func_vfork(self):
        # setup the defs 
        self.check_header('vfork.h')

        # check the function
        return self.check_func_fork(fcn='vfork')
        
    #AC_PROG_GCC_TRADITIONAL

    def check_func_stat(self):
        """Emulate AC_FUNC_STAT"""
        ok = self.check_header('sys/stat.h')
        return self.check_lib('stat')


    def check_func_lstat(self):
        # do we have it
        ok = self.check_lib('lstat')
        if not ok:
            return False

        # should check if it does proper dereferencing
        self.check_msg('whether lstat correctly handles trailing slash')

        # test files
        testfile = os.path.join(self.tdir, 'conftest_lstat.file')
        symfile = testfile.replace('.file', '.sym')

        # tidy up
        try:
            os.unlink(testfile)
        except FileNotFoundError:
            pass
        try:
            os.unlink(symfile)
        except FileNotFoundError:
            pass

        # lastly, run it...
        try:
            # make a basic file
            with open(testfile, 'w') as tfd:
                tfd.write('garbage' + os.linesep)
            
            # setup the framework
            os.symlink(testfile, symfile)
        
        except NotImplementedError as nie:
            self.log.write("failed to create symlink for test: " + symfile)
            return False
        
        # compile and run
        ok = self._check_run(main=[
            'struct stat sbuf;',
            'return lstat ("{}/", &sbuf) == 0;'.format(symfile)
            ],
            includes=self.includes
        )

        if not ok:
            self.check_msg_result('no')
            return False

        # setup the macro for the special functionality
        self.add_macro('LSTAT_FOLLOWS_SLASHED_SYMLINK', 1)
        self.check_msg_result('yes')
        return True
        
    def check_getpw_r__posix(self):
        self.check_msg('getpw*_r are posix like')

        ok = self._check_compile(
            includes=['stdlib.h', 'sys/types.h', 'pwd.h'],
            main=[
                'getpwnam_r(NULL, NULL, NULL, (size_t)0, NULL);',
                'getpwuid_r((uid_t)0, NULL, NULL, (size_t)0, NULL);'
                ]
            )
        
        if not ok:
            self.check_msg_result('no')
            return False
        
        self.check_msg_result('yes')
        self.add_macro('HAVE_GETPW_R_POSIX', 1)
        return True
    
    def check_getpw_r__draft(self):
        self.check_msg('getpw*_r are draft like')
        
        ok = self._check_compile(
            includes=['stdlib.h', 'sys/types.h', 'pwd.h'],
            main=[
                'getpwnam_r(NULL, NULL, NULL, (size_t)0);',
                'getpwuid_r((uid_t)0, NULL, NULL, (size_t)0);'
                ]
        )

        if not ok:
            self.check_msg_result('no')
            return False

        self.check_msg_result('yes')
        self.add_macro('HAVE_GETPW_R_DRAFT', 1)
        return True


def check_system():
        """Run the system inspection to create config.h"""
        # setup the configurator
        ctool = Configure('conf_edit', debug=True, tmpdir='/tmp/conf_test')
        ctool.package_info('libedit', '3.1', '20180321')

        # early items...
        ctool.check_stdc()
        ctool.check_use_system_extensions()

        # check for the necessary system header files
        ctool.check_headers([
            'fcntl.h', 'limits.h', 'malloc.h', 'stdlib.h', 'string.h',
            'sys/ioctl.h', 'sys/param.h', 'unistd.h', 'sys/cdefs.h',
            'dlfcn.h', 'inttypes.h'])

        # some uncommon headers
        ctool.check_header_dirent()
        ctool.check_header_sys_wait()
        
        # figure out which terminal lib we have
        for testlib in ['tinfo', 'ncurses', 'ncursesw', 'curses', 'termcap']:
            ok = ctool.check_lib('tgetent', testlib)
            if ok:
                break
        
        # check for terminal headers
        term_headers = ['curses.h', 'ncurses.h', 'termcap.h']
        oks = ctool.check_headers(term_headers)
        if True not in oks:
            raise ConfigureError("Must have one of: " + ', '.join(term_headers))

        # must have termios.h
        ok = ctool.check_header('termios.h')
        if not ok:
            raise ConfigureError("'termios.h' is required!")

        # must have term.h
        ctool.check_header('term.h')

        #AC_C_CONST
        ctool.check_type_pid_t()
        ctool.check_type_size_t()
        ctool.check_type('u_int32_t')
        
        #AC_FUNC_CLOSEDIR_VOID
        ctool.check_func_fork()
        ctool.check_func_vfork()
        #AC_PROG_GCC_TRADITIONAL
        ctool.check_type_signal()
        #AC_FUNC_STAT


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

        ctool.check_func_lstat()
            
        # these probably should be local
        ctool.check_getpw_r__posix()
        ctool.check_getpw_r__draft()
            
        #print("exlibs3:", exlibs)
        #print("libs3:", ctool.libraries)

        ctool.dump()
        
        # looks good - add the extra libraries if any
        #clib['libraries'] += ctool.libraries

        # locate the config template and output
        #config_h = os.path.join(self.build_temp, self.libedit_dir, 'config.h')
        #config_h_in = os.path.join(self.libedit_dir, 'config.h.in')
        config_h = '/tmp/config.h'
        config_h_in = '/home/mjn/work/python/pe-test/src/libedit/config.h.in'
        
        # barf out the config.h file from config.h.in
        ctool.generate_config_h(config_h, config_h_in)
        ctool.generate_config_log(config_h.replace('.h','.log'))
        
        # done
        return ctool



        
if __name__ == '__main__':
    if False:
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

    else:
        check_system()
