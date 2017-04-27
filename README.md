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

### Annoyances

I am vexed and cannot understand why Modules/main.c in the Python build does this

```sh
v = PyImport_ImportModule("readline");
```

I've commented it out and found no alteration of functionality.  It *probably* is some legacy code which was put in in the dark-ages, and just doesn't piss anyone off....   except me.

## Testing

The test matrix so far is this:

| Distribution | Version | Python  | Libedit | Link | State |
| ------ | ------ | ------ | ------ | ------ | ------ |
| Ubuntu | 16.04LTS | 3.7 | http://thrysoee.dk/editline/ | Dynamic | Works |
| Ubuntu | 16.04LTS | 3.7 | http://thrysoee.dk/editline/ | Static | Works |
| RedHat | * | ? | http://thrysoee.dk/editline/ | Dynamic | Not-Tested |
| FreeBSD | 10.3 | 3.7 | installed | Dynamic | Works |
| NetBSD | 7.1 | 3.7 | installed | Dynamic | Works |
| OpenBSD | 6.1 | 3.7 | installed | Dynamic | Works |
| MacOS | ? | ? | installed | ? | Not-Tested |
| SunOS | ? | ? | ? | ? | Not-Tested |

  It needs to be tested in both dynamic and static link methods.  (By 'static' it is where the _editline.so python extension has the libedit sources directly incorporated into itself, instead of requiring libedit.so.)

## Quirks

FreeBSD
  - libedit/histedit.h has no versioning what-so-ever

OpenBSD
  - libedit.so does not have linker info to additional libs it needs [termcap]
  

## Tasks

The baseline code is working.  It is considerably simpler than the readline implementation and also uses instances (even the 'system' one) so it can support multiple instances per interpreter.

   - Make a more complete fileset/install/build so it can be shared more easily
   - Create changeset for Python codebase (integrate everything there?)
   - Update autoconf to properly detect and identify readline and libedit
   - Setup a formal choice (cmdline option?) to select which one is "default"
   - Create a test_editline.py infrastructure to beat it like a rented mule
   - build out functionality for
       * bind
       * el_get
       * el_set
   - create a mapping routine so 'parse-and-bind' can support a common command format and translate to the "local" flavour.
   - test with
      * python -i
      * idle
      * ipython

##### Nice-To-Haves:
   - leverage the libedit tokenizer to do more indepth parsing

## License

 This is going to be BSD-licensed, or whatever libedit goes by.  This should be available to everyone freely.
 