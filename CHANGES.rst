Python-Editline Changelog
=========================

Version 1.0.1
-------------

Major upgrade to setup infrastructure

- Removed ALL external calls to autoconf/configure scripts
- Removed all dependencies on 'make', 'awk', ... inherited from autoconf
- Added Configure class which does most of the necessary autoconf stuff
  in pure python
- Added support to strip the final .so to save space

Version 1.0.0
-------------

Initial release to PyPi.

- Functionality is pretty well tested
- Verified Linux, FreeBSD, NetBSD, SunOS, Mac
- Rechecked 3.3 support
- Corrected packaging issues during TestPyPi

Version 0.1.0
-------------

Initial release to TestPyPi.

- Functionality is pretty well tested
- Verified Linux, FreeBSD, NetBSD, SunOS, Mac

Version 0.0.1
-------------

Created the working package.
