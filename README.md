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
# cd python-editline
# make 
# pyvenv3 venv
# . venv/bin/activate
(venv) # python3 setup.py install 
(venv) # cp siteconfig/sitecustomize.py  VENV/lib/python3.?/site-packages
(venv) # python
>>>
```
The 'gnu make' is there to download and prep the libedit distribution.

After building the module itself, the trick is getting it to kick in.  That is done in site.py.  Unfortunately, when using a Virtual-ENV, it *does not* actually give you the chance (by default) to put in site.py.

 Sooooo....  That is why I copy over the original, into the VENV, patch it with the fix (as I figure you don't want to bork your actual install), then you must run with the extra PYTHONPATH setting, because that goes on the FRONT of sys.path.  Yay!  It now picks up the site.py from the VENV.
 
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

I've commented it out and found no alteration of functionality.  It *probably* is some legacy code which was put in in the dark-ages, and just doesn't piss anyone off....   except me.  Its presences *seems* benign, but it still concerns me.

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

### RedHat
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom| idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| * | ? | [thrysoee.dk](http://thrysoee.dk/editline/) | Dynamic |  |  |  |

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
| Version | Python  | Libedit | Link | Python -i | Custom | idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| NetBSD | 7.1 | 3.7 | installed | Dynamic | Works |  |  |

### OpenBSD
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom | idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| OpenBSD | 6.1 | 3.7 | installed | Dynamic | Works |  |  |

#### Quirks
  - libedit.so does not have linker info to additional libs it needs [termcap]

### MacOS
#### Testing
| Version | Python  | Libedit | Link | Python -i | Custom | idle |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| MacOS | ? | ? | installed | ? | Not-Tested |  |  |

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

## Acknowledgements

 Thank you to
   * http://thrysoee.dk/editline/ for creating the portable version of the NetBSD 'libedit' library.
   * the libedit developers who made the examples/ directory.  Great baseline code.