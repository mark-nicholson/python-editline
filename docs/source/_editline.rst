
.. py:module:: editline._editline

Detailling the C-API based code implementing the primary
libedit interface.

The C-code has some documentation of its own (in comments) and
has added basic docstrings for each item.  Sphinx does not seem
to be able to pull those out unfortunately.


.. py:class:: EditLineBase(name: str, in_stream: object, out_stream: object, err_stream: object) -> object
   :module: editline._editline

      Bases: :class:`object`

      This is the base-interface class for binding to NetBSD's libedit library.
      It implements a similar functionality as readline.so but using a different API.  (It *does* have a `readline` API but that has been tried and beaten a lot in the readline extension to moderate avail.  It has greatly over complicated that extension and really does not work too well...)
   
      :param name:       A name of the instance
      :param in_stream:  A file-like object where the `input` is pulled
      :param out_stream: A file-like object where the `output` is pushed
      :param err_stream: A file-like object where the `errors` are pushed

      :returns: EditLineBase class instance

      .. :rubrik: Notes

      Each `stream` must implement the `fileno()` member function so that a C FILE handle can be opened and used based on that `fileno`.


   .. py:attribute::  EditLineBase.H_ADD
      :module: editline._editline
      :annotation: cmd value for history() api to add a history command
		
   .. py:attribute::  EditLineBase.H_APPEND
      :module: editline._editline
      :annotation: cmd value for history() api to append a history command

   .. py:attribute::  EditLineBase.H_CURR
      :module: editline._editline
      :annotation: cmd value for history() api to get the current entry

   .. py:attribute::  EditLineBase.H_DEL
      :module: editline._editline
      :annotation: cmd value for history() api to delete a history command

   .. py:attribute::  EditLineBase.H_ENTER
      :module: editline._editline
      :annotation: cmd value for history() api to add a new history command

   .. py:attribute::  EditLineBase.H_FIRST
      :module: editline._editline
      :annotation: cmd value for history() api to get the first history command

   .. py:attribute::  EditLineBase.H_GETSIZE
      :module: editline._editline
      :annotation: cmd value for history() api to return the size of th history

   .. py:attribute::  EditLineBase.H_GETUNIQUE
      :module: editline._editline
      :annotation: cmd value for history() api to only store unique commands



   .. py:attribute::  EditLineBase.prompt
      :module: editline._editline
      :annotation: set the command-line prompt string (default '>>> ')

   .. py:attribute::  EditLineBase.rprompt
      :module: editline._editline
      :annotation: set the command-line right-side prompt string

   .. py:attribute::  EditLineBase.in_stream
      :module: editline._editline
      :annotation: terminal interface file-like object for `stdin`

   .. py:attribute::  EditLineBase.out_stream
      :module: editline._editline
      :annotation: terminal interface file-like object for `stdout`

   .. py:attribute::  EditLineBase.err_stream
      :module: editline._editline
      :annotation: terminal interface file-like object for `stderr`


   .. py:method:: EditLineBase._completer(text: str) -> list
      :module: editline._editline
   
      Compute matching attributes to an object.
      
      :param text: the command-line text to be completed
      
      :returns: All available commands which have `text` as a prefix.
      
      .. rubric:: Notes
      
      This routine is, effectively, a Python callback from libedit's completion
      coding from within the C-API. The goal is to do the bulk of the command
      "figuring-out" in Python where it is sooooo much easier to manage lists
      of strings.
      
      .. warning::
      
         This routine is a *default* and must be overidden in a subclass.


   .. py:method:: EditLineBase.delete_text(count: int)
      :module: editline._editline
   
      Scrub out `count` characters of the command-line at the current position
      
      :param count: count of characters to be removed
      
      :returns: Nothing


   .. py:method:: EditLineBase.insert_text(text: str)
      :module: editline._editline
   
      Insert some additional text onto the command line at the current position.
      
      :param text: the text string to be inserted into the current command-line
      
      :returns: Nothing

	     
   .. py:method:: EditLineBase.readline() -> str
      :module: editline._editline
   
      Engage the user interactively in a tab-completion enable input.
      
      :returns: string input by user


   .. py:method:: EditLineBase.redisplay()
      :module: editline._editline
   
      Force the terminal library to re-draw the current command-line.
      
      :returns: Nothing


   .. py:method:: EditLineBase.history(cmd: int, *args)
      :module: editline._editline
   
      Direct interface to libedit's `history` API.

      :param cmd: an H_ constant from the class
      :param args: arguments vary based on the cmd 
      
      :returns: Varies based on the cmd

      .. rubric:: Notes
      
      The details for arguments pertaining to each H\_ command value are best
      documented in libedit's history.3 man-page.


   .. py:method:: EditLineBase.read_history_file(read_history_file: str) -> int
      :module: editline._editline
   
      Load the given filename into the history buffer.  The format of 
      this file is defined by libedit itself and is best generated with
      write_history_file().

      :param fname: filename of the file to load into history

      :returns: Error code on failure or 0 on success


   .. py:method:: EditLineBase.write_history_file(write_history_file: str) -> int
      :module: editline._editline
   
      Write out the accumulated history of commands input in this instance
      to a file of the given name.

      :param fname: filename of the file to write

      :returns: Error code on failure or 0 on success


  .. :rubrik: Infrastructure Notes

  The general implementation of this module contains two aspects:

     - EditLineBase class for instances of interpreters
     - Module global initializations for system interface (`python -i`)

  In order to engage the terminal completion using editline, it is necessary
for it to be loaded and setup with a lineeditor instance.  The EditLineBase
subclass provides the more specific support for Python's interpreter (or a
custom one if you build it) and works with lineeditor to provide the fancier
functionality of the tab-completer.  To configure the global instance, the
code is:

.. code-block:: python
   :caption: EditLine Bootstrap

     from editline import _editline
     from editline.editline import EditLine
     from editline import lineeditor
     editline_system = _editline.get_global_instance()
     if editline_system is None:
         sys_el = EditLine("PythonSystem", sys.stdin, sys.stdout, sys.stderr)
         _editline.set_global_instance(sys_el)

         sys_line_ed = lineeditor.EditlineCompleter(sys_el)
         lineeditor.global_line_editor(sys_line_ed)


This code is implemented in the sitecustomize.py file distributed (and installed!) by this package.

   Libedit works on a *per-instance* basis which is quite unlike libreadline's  mess of global variables.  Likewise, the Python infrastructure for EditLine follows libedit's lead.

   To that end, the code above is:

   - Creating the *global* instances of an EditLine and a Completer
   - These are each registered with their respective modules so that other imports of the modules can gain access to those instances.  This is more-or-less like doing `import readline`.

   There are further details of how to weave the infrastructure into the Python interpreter's mechanics.  Have a look at `sitecustomize.py` for the gory details.

   The mechanics which are *not* apparent from `sitecustomize.py` are the C-API bindings done in _editline.so.

   A (global) callback is registered with the Python runtime which is called in interactive mode to engage the readline functionality.  This routine is a C-function *only*, called ``call_editline()``.  Its interface is defined by the Python infrastructure and it depends on having a valid instance of an EditLineBase subclass initialized and registered *before* the terminal is used.   Hence the code in `sitecustomize.py`.  This is emulated from the `readline` implementation.

