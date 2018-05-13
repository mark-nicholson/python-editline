Testing
=======

For most platforms, there are 3 implementations which need to be tested

- dynamically linked to "system installed" libedit.so
- dynamically linked to manually built `thrysoee.dk`_
- libedit srcs built directly into the \_editline.so module

In those states, I would like to verify - python -i - custom shell -
idle (will probably need a patch)

IPython - No testing required here. They abandoned 'readline' a while
ago and use 'prompt\_toolkit'.


Python Versions
---------------

Highlights:

* 3.7b   - Works Well
* 3.6    - Works Well
* 3.5    - Works Well
* 3.4    - Works Well
* 3.3    - Hacked in some changes to the c-module to backport to support PyMem\_RawMalloc which was introduced in 3.4
* <= 3.2 - Needs c-module backporting due to C-API changes.
* 2.x    - Its *officially* dead.  Didn't bother; it would be huge work.


Platforms
---------

.. toctree::
   :maxdepth: 2

   testing/ubuntu
   testing/solus
   testing/freebsd
   testing/openbsd
   testing/netbsd
   testing/sunos
   testing/redhat
   testing/macos


.. _thrysoee.dk: http://thrysoee.dk/editline/
