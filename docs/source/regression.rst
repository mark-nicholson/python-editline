Regression
==========

I did not fully automate the regression, but did create some scripts to
help the process. I setup a regression directory like this:

::

    - regression
        |- srcs
        |- tarballs
        |- ubuntu
        |- freebsd11
        |- netbsd7
        |- solaris11
        |- openbsd6

and dropped in the scripts from the regression/ directory. You'll need
to tweak the scripts to get the pathing right for your exact setup.

The process goes like this:

1. ``make`` downloads a tarball of each Python release (3.X) to test
   clone git repos of libedit and libffi extract the tarballs into srcs
2. ``mkdir ubuntu``
3. ``cd ubuntu``
4. ``ln -s ../Makefile.plat Makefile``
5. ``make VER=3.6.1`` Repeat this for each version of Python you grabbed
6. ``../scripts/do_editline.sh 'venv-3.6.1-*'`` Yes, the SINGLE QUOTES
   are important. This builds the editline extension and installs it.
7. ``script test_3.6.1.log; ../scripts/check_editline.sh 'venv-3.6.1-*'; end``
   This runs the unittest support for all builds of that Python version
   Need to use 'script' to capture the output because redirecting/piping
   mucks with the terminal so some of the tests fail.
8. Repeat steps 5-8 for each Python version you have.

