# Python-Editline

A repository to create a Python extension which links to libedit.so and implements the shell-completion functionality completely independent of libreadline.so and readline.

My operational goal was originally to try to get the readline functionality of libedit to "just work".  Apparently me, and a bazillion others have tried and only got something marginally functional.

 I changed the plan.  For reasons I do not know, the 'readline' interface of Python is heavily favouring the libreadline.so interface.  In my view,  that is a problem on several fronts.  It makes portability to libedit a pain, and have you seen how many freeking global variable libreadline uses just to function?  It is crazy.
 
 My (so far successful) approach has been to abandon the readline api and work towards a generic line-editor interface to which both libedit (and readline if necessary) will conform.

### The goals are:

  - to create a Python installation devoid of GPL
  - run correctly on Linux, *BSD, SunOS and Mac
  - not muck up the current terminal
  - use libedit either built-in on various BSDs or use http://thrysoee.dk/editline/
  - push it back into Python main-line
  - Move the bulk of the "completion" functionality back into Python code where it is a hell of a lot easier to manage lists of strings

### Current State

I have done various tries at this.  The module/ directory is so far the one that works.

  - Basic tab completion runs smoothly (... in Python code)
  - interface starts up automatically with 'python -i'
  - system-wide editline instance is created automatically
  - terminal resizing works
  - support for RIGHT-SIDE prompt (as well as std) is present (I don't think readline can even do that)
  - support for ^c and ^d match the readline functionality
  - no noticeable terminal changes occur after running
  - history support works
     * adding commands
     * loading history file
     * saving history file
  - setup.py will construct either an extension which refers to libedit.so or will build a larger extension with the libedit sources embedded.

## Get it Working

To get this thing working, I recommend this:

```bash
# cd /handy/location
# git clone https://github.com/mark-nicholson/python-editline.git
# make 
# pyvenv3 venv
# . venv/bin/activate
(venv) # python3 setup.py install 
(venv) # cp siteconfig/sitecustomize.py  VENV/lib/python3.?/site-packages
(venv) # python
>>>
```
The 'gnu make' is there to download and prep the libedit distribution.

A note of caution before you pull all of your hair out.  SOME distributions (pointing at you Ubuntu) drop in a sitecustomize.py file in /usr/lib/python...  which is EXTREMELY annoying as it completely prevents a VirtualENV from creating its own 'customization' using this because the system path is always ahead of the venv path.  sigh.  You can hack this by renaming it to usercustomize.py and dropping it at the same place -- ugly but effective.

I tested this in both a default install and virtual-env.  The instructions detail the VENV method which I used most.  The sitecustomize.py file is critical as it is the init-hook which disengages readline as the default completer and installs editline.

Another way to make it work in a default install, you can edit site.py and replace the enablerlompleter() function with the enable_line_completer() function from sitecustomize.py in the repo.  It does not matter whether you do it in the cpython source tree, or after it is installed.  It is coded in such a way that if editline support is absent, it will still fall back to readline.

 How do I check?
 
 ```python
 >>> import _editline
 >>> gi = _editline.get_global_instance()
 >>> gi.rprompt = '<RP'
 >>>                                                              <RP
 >>> 
 ```
 
Get readline to do THAT!  (ok, if your browser is narrow, you should have the '<RP' on the other end of the command line -- the interpreter should do it right)
    
Premise?  Ok, so the editline infra uses instances, NOT GLOBALS.  the get_global_instance() API gives you "roughly" the same thing as 'import readline'.  We will see if we can smooth it out a bit more later.


### Annoyances

I am vexed and cannot understand why Modules/main.c in the Python build does this

```sh
v = PyImport_ImportModule("readline");
```

I've commented it out and found no alteration of functionality.  It *probably* is some legacy code which was put in in the dark-ages, and just doesn't piss anyone off....   except me.  Its presences *seems* benign, but it still concerns me.  Even when, disconcertingly, both readline.so is loaded (by main.c) and _editline.so is loaded by the standard method, this then has both libreadline.so and libedit.so loaded into the process.  There will certainly be a symbol-collision for 'readline()' (in C) as both have it.  I suspect that it will work without any issues since _editline.so only calls the libedit API (el_*) and does not reference the C call to readline() in libedit.  Tread carefully.

If you are rolling your own Python interpreter, patch out the silly import in main.c.  Then, even if you have both readline.so and _editline.so, they will be mutually exclusive!  (Check the patches/ directory.)

## Testing

 For most platforms, there are 3 implementations which need to be tested
  - dynamically linked to "system installed" libedit.so
  - dynamically linked to manually built [thrysoee.dk](http://thrysoee.dk/editline/) libedit.so
  - directly linked into the _editline.so module

 In those states, I would like to verify
   - python -i
   - custom shell
   - idle (will probably need a patch)

IPython - No testing required here.  They abandoned 'readline' a while ago and use 'prompt_toolkit'.

## Tasks

The baseline code is working.  It is considerably simpler than the readline implementation and also uses instances (even the 'system' one) so it can support multiple instances per interpreter.

   - Make a more complete fileset/install/build so it can be shared more easily
   - Create changeset for Python codebase (integrate everything there?)
   - Update autoconf to properly detect and identify readline and libedit
   - Setup a formal choice (cmdline option?) to select which one is "default"
   - Create a test_editline.py infrastructure to beat it like a rented mule
   - build out functionality for
       * bind()
       * el_get()
       * el_set()
       * history()
   - create a mapping routine so 'parse-and-bind' can support a common command format and translate to the "local" flavour.
   - potentially create a subclass which is a readline drop-in-replacement.

##### Nice-To-Haves:
   - leverage the libedit tokenizer to do more indepth parsing

## Platforms

Tried 3.3.6 but there is a link error with the .so.  PyMem_RawMalloc was introduced in 3.4.  Would need to backport something to support 3.3 and earlier.  I did not even attempt 2.*.

### Ubuntu

#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom |  idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| 16.04LTS | 3.7.0a | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 16.04LTS | 3.7.0a | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 16.04LTS | 3.7.0a | installed | lib.so | Works |  |  |
| 16.04LTS | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 16.04LTS | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 16.04LTS | 3.6.1 | installed | lib.so | Works |  |  |
| 16.04LTS | 3.5.3 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 16.04LTS | 3.5.3 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 16.04LTS | 3.5.3 | installed | lib.so | Works |  |  |
| 16.04LTS | 3.4.6 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 16.04LTS | 3.4.6 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 16.04LTS | 3.4.6 | installed | lib.so | Works |  |  |

#### Quirks
None

### RedHat
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom| idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| * | ? | [thrysoee.dk](http://thrysoee.dk/editline/) | Dynamic |  |  |  |

#### Quirks
- Probably should test this but since Ubuntu passed, I'm guessing just about any Linux distro will work; at least with the custom or built-in model.

### FreeBSD
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom |  idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| 11.0 | 11.0 | 3.7 | installed | Dynamic | Works |  |  |
| 11.0 | 3.7.0a | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 11.0 | 3.7.0a | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 11.0 | 3.7.0a | installed | lib.so | Works |  |  |
| 11.0 | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 11.0 | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 11.0 | 3.6.1 | installed | lib.so | Works |  |  |
| 11.0 | 3.5.3 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | BusError |  |  |
| 11.0 | 3.5.3 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | SegFault |  |  |
| 11.0 | 3.5.3 | installed | lib.so | Works |  |  |
| 11.0 | 3.4.6 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 11.0 | 3.4.6 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 11.0 | 3.4.6 | installed | lib.so | Works |  |  |

#### Quirks
  - libedit/histedit.h has no versioning what-so-ever

### NetBSD
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom |  idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| 7.1 | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 7.1 | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 7.1 | 3.6.1 | installed | lib.so | Works |  |  |
| 7.1 | 3.5.3 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | BusError |  |  |
| 7.1 | 3.5.3 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | SegFault |  |  |
| 7.1 | 3.5.3 | installed | lib.so | Works |  |  |
| 7.1 | 3.4.6 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 7.1 | 3.4.6 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 7.1 | 3.4.6 | installed | lib.so | Works |  |  |

#### Quirks
- Python 3.7.0a failed to build so it could not be tested like the other releases...
  (Ctypes/libffi issue -- unrelated to libedit!)

### OpenBSD
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom | idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| OpenBSD | 6.1 | 3.7 | installed | Dynamic | Works |  |  |

#### Quirks
  - libedit.so does not have linker info to additional libs it needs [termcap]
  - I did not do the comprehensive version testing here.

### MacOS
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom | idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| 10.11 | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 10.11 | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 10.11 | 3.6.1 | installed | lib.so | Works |  |  |

#### Notes
- I ran into many problems trying to get Python to build and function at all.  Consistent problems with 'SegFault 11', which seemed to be related to ctypes/ffi.  I was not able to verify the other versions.  Python 3.6.1 was available from 'brew' and I installed that and then used it as a baseline for the virtual-envs to test editline.

### Solaris
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom |  idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| 11.3 | 11.0 | 3.7 | installed | Dynamic | Works |  |  |
| 11.3 | 3.7.0a | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 11.3 | 3.7.0a | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 11.3 | 3.7.0a | installed | lib.so | Works |  |  |
| 11.3 | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 11.3 | 3.6.1 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 11.3 | 3.6.1 | installed | lib.so | Works |  |  |
| 11.3 | 3.5.3 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | BusError |  |  |
| 11.3 | 3.5.3 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | SegFault |  |  |
| 11.3 | 3.5.3 | installed | lib.so | Works |  |  |
| 11.3 | 3.4.6 | [thrysoee.dk](http://thrysoee.dk/editline/) | lib.so | Works |  |  |
| 11.3 | 3.4.6 | [thrysoee.dk](http://thrysoee.dk/editline/) | builtin | Works |  |  |
| 11.3 | 3.4.6 | installed | lib.so | Works |  |  |

#### Quirks
   - libffi is in place by default, but headers are not in /usr/include (I symlinked them -- they are on the system, just not in the correct place)  
   - you need to manually install GAWK >= version 4.0

## Regression

I did not fully automate the regression, but did create some scripts to help the process.  I setup a regression directory like this:

```
- regression
    |- srcs
    |- tarballs
    |- ubuntu
    |- freebsd11
    |- netbsd7
    |- solaris11
    |- openbsd6
```

and dropped in the scripts from the regression/ directory.  You'll need to tweak the scripts to get the pathing right for your exact setup.

The process goes like this:

1. make tarballs
     downloads a tarball of each Python release (3.X) to test
     download the tarball of libedit 
2. make extract
       extract the tarballs into srcs
3.  cd ubuntu
4. ln -s ../Makefile.plat Makefile
5. make VER=3.6.1
    Repeat this for each version of Python you grabbed
6. ../do_editline.sh 'venv-3.6.1-*'
    Yes, the SINGLE QUOTES are important.  This builds the editline extension and installs it.
7. ../tidy_editline.sh 'venv-3.6.1-*'
    This installs the sitecustomize.py file
8. ../ck_el.sh 'venv-3.6.1-*'
     This runs the unittest support for all builds of that Python version
9. Repeat steps 5-8 for each Python version you have.

## Acknowledgements

 Thank you to
   * http://thrysoee.dk/editline/ for creating the portable version of the NetBSD 'libedit' library.
   * the libedit developers who made the examples/ directory.  Great baseline code.