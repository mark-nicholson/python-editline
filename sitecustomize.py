"""
Site-Customize

Template file to put into a virtual-env to implicitely engage the editline
completer instead of readline (whether or not it is present)
"""

import sys
import os

def enable_line_completer():
    """Enable default line-editor configuration on interactive prompts, by
    registering a sys.__interactivehook__.

    Try to register support from either editline or readline.
    If the readline module can be imported, the hook will set the Tab key
    as completion key and register ~/.python_history as history file.
    """
    def register_readline():
        """Attempt to configure the readline completion support"""
        import atexit
        try:
            import readline
            import rlcompleter
        except ImportError:
            return

        # Reading the initialization (config) file may not be enough to set a
        # completion key, so we set one first and then read the file.
        readline_doc = getattr(readline, '__doc__', '')
        if readline_doc is not None and 'libedit' in readline_doc:
            readline.parse_and_bind('bind ^I rl_complete')
        else:
            readline.parse_and_bind('tab: complete')

        try:
            readline.read_init_file()
        except OSError:
            # An OSError here could have many causes, but the most likely one
            # is that there's no .inputrc file (or .editrc file in the case of
            # Mac OS X + libedit) in the expected location.  In that case, we
            # want to ignore the exception.
            pass

        if readline.get_current_history_length() == 0:
            # If no history was loaded, default to .python_history.
            # The guard is necessary to avoid doubling history size at
            # each interpreter exit when readline was already configured
            # through a PYTHONSTARTUP hook, see:
            # http://bugs.python.org/issue5845#msg198636
            history = os.path.join(os.path.expanduser('~'),
                                   '.python_history')
            try:
                readline.read_history_file(history)
            except IOError:
                pass
            atexit.register(readline.write_history_file, history)

    def register_editline():
        """Attempt to configure the editline completion support"""
        import atexit
        try:
            import _editline
            from editline import editline
            from lineeditor import EditlineCompleter
            editline_system = _editline.get_global_instance()
            if editline_system is None:
                editline_system = editline("PythonSystem",
                                           sys.stdin, sys.stdout, sys.stderr)
                _ = EditlineCompleter(editline_system)
                _editline.set_global_instance(editline_system)
        except ImportError:
            return

        # the binding of ^I (tab) to the completer is done in _editline
        # by default.  The user can override it, but the default is correct.

        # pull in the libedit defaults
        try:
            editrc = os.path.join(os.path.expanduser('~'), '.editrc')
            editline_system.read_init_file(editrc)
        except OSError:
            # An OSError here could have many causes, but the most likely one
            # is that there's no .inputrc file (or .editrc file in the case of
            # Mac OS X + libedit) in the expected location.  In that case, we
            # want to ignore the exception.
            pass

        if editline_system.get_current_history_length() == 0:
            # If no history was loaded, default to .python_history.
            # The guard is necessary to avoid doubling history size at
            # each interpreter exit when readline was already configured
            # through a PYTHONSTARTUP hook, see:
            # http://bugs.python.org/issue5845#msg198636
            history = os.path.join(os.path.expanduser('~'), '.python_history')
            try:
                editline_system.read_history_file(history)
            except IOError:
                pass
            atexit.register(editline_system.write_history_file, history)

    # snoop to see which is available don't import the modules, just check
    # for a valid loader so we don't pollute the namespace accidentally.
    import pkgutil
    le_loader = pkgutil.get_loader('lineeditor')
    el_loader = pkgutil.get_loader('editline')
    _el_loader = pkgutil.get_loader('_editline')
    rl_loader = pkgutil.get_loader('readline')

    # prefer editline
    if le_loader and el_loader and _el_loader:
        sys.__interactivehook__ = register_editline
    elif rl_loader:
        sys.__interactivehook__ = register_readline
    else:
        sys.__interactivehook__ = None



def main():
    """Mimick the format of the true site.py

    This function is called automatically when this module is imported,
    unless the python interpreter was started with the -S flag.
    """
    enable_line_completer()


# Prevent extending of sys.path when python was started with -S and
# site is imported later.
if not sys.flags.no_site:
    main()
