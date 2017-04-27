# Python-Editline

A repository to create a Python extension which links to libedit.so and implements the shell-completion functionality completely independent of libreadline.so and readline.

### The goals are:

  - to create a Python installation devoid of GPL
  - run correctly on Linux, *BSD, SunOS and Mac
  - not muck up the current terminal
  - use libedit either built-in on various BSDs or use http://thrysoee.dk/editline/
  - push it back into Python main-line

### Current State

I have done various tries at this.  The module/ directory is so far the one that works.

### Annoyances

I am vexed and cannot understand why Modules/main.c in the Python build does this

```sh
v = PyImport_ImportModule("readline");
```

I've commented it out and found no alteration of functionality.  It *probably* is some legacy code which was put in in the dark-ages, and just doesn't piss anyone off....   except me.

## Testing

The test matrix so far is this:

| Distribution | Version | Libedit | State |
| ------ | ------ | ------ | ------ |
| Ubuntu | 16.04LTS | http://thrysoee.dk/editline/ | Works |
| RedHat | ? | http://thrysoee.dk/editline/ | Not-Tested |
| FreeBSD | 10.3 | installed | Works |
| NetBSD | 7.1 | installed | Works |
| OpenBSD | 6.1 | installed | Works |
| MacOS | ? | installed | Not-Tested |
| SunOS | ? | ? | Not-Tested |

## Tasks

The baseline code is working.  It is considerably simpler than the readline implementation and also uses instances (even the 'system' one) so it can support multiple instances per interpreter.

   - Create changeset for Python codebase (integrate everything there?)
   - Update autoconf to properly detect and identify readline and libedit
   - Setup a formal choice (cmdline option?) to select which one is "default"
   - Create a test_editline.py infrastructure to beat it like a rented mule

## License

 This is going to be MIT-licensed, or whatever libedit goes by.  This should be available to everyone freely.
 