Regression
==========

There is now a, more or less, fully automated regression. I setup a
regression directory like this:

::

    - regression     (static)
      |- regress.sh

    - regression     (dynamic)
      |- tarballs
      |- srcs
      |- 3.4.7
      |- ...
      |- 3.7.0b2
      |- libedit
      |- gawk (optional)
      
The ``regress.sh`` script implements a vast amount of functionality
all in POSIX /bin/sh -- for portability.  I had run into various issue
trying to get gmake and bmake to agree on a Makefile, then gave up.
The shell-script now does even more than the preceeding Makefiles
with *some* dependency checks.

The process goes like this:

1. ``./regress.sh fetch`` - downloads a tarball of each Python release (3.X) 
   to test, along with libedit and tools. It also extracts the tarballs
   into `srcs`.
2. ``./regress.sh venvs`` - builds Python versions and all virtual-envs
3. ``./regress.sh install`` - installs pyeditline via PIP into each virtual-env
4. ``script test.log``  - log the console. This is necessary because the
   extension must run in a TTY -- redirections fail miserably      
5. ``./regress.sh check`` - runs the unittest on every virtual-env
6. ``exit`` - End the `script` session.


Configurations
--------------

The `regress.sh` script mainly looks at environment-variables for configuration.
Overriding these can be helpful to do specific testing.

VER - Sets the versions of Python to work with. (Quote it for multiple.)
CFG - Sets the configurations to test -- default: "dist builtin custom"

Have a look at:

``regress.sh help``

to gain more insight into the commands and usage.  For those of you who are
hard-core -- read the source.
