MacOS
=====

.. include:: ../common/subs.rst

Testing
-------

+-----------+-----------+-----------------------------+-----------+-------------+----------+
|  Version  |  Python   | Libedit                     | Link      | Manual Test | UnitTest |
+===========+===========+=============================+===========+=============+==========+
|   10.11   |   3.6.1   | `thrysoee.dk`_              | lib.so    |     OK      |          |
+-----------+-----------+-----------------------------+-----------+-------------+----------+
|   10.11   |   3.6.1   | `thrysoee.dk`_              | builtin   |     OK      |          |
+-----------+-----------+-----------------------------+-----------+-------------+----------+
|   10.11   |   3.6.1   | pre-installed               | lib.so    |     OK      |          |
+-----------+-----------+-----------------------------+-----------+-------------+----------+


Notes
-----

*  I ran into many problems trying to get Python to build and function
   at all. Consistent problems with 'SegFault 11', which seemed to be
   related to ctypes/ffi. I was not able to verify the other versions.
   Python 3.6.1 was available from 'brew' and I installed that and then
   used it as a baseline for the virtual-envs to test editline.


