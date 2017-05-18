"""
Comprehensive command line completer support

Provides extended tab-completions support for
    - std items: keywords, attributes
    - import statements
    - array indicies
    - dict keys

It is based on the code from rlcompleter, then pimped out.
"""

import sys
import re
import keyword
import pkgutil

import builtins
import __main__

#from types import

__all__ = ["Completer", "ReadlineCompleter", "EditlineCompleter"]


class Completer:
    """Tab-Completion Support

    Provides extended tab-completion mechanisms in a way which is available
    to both 'readline' and 'editline'.
    """

    # this re will match the last 'unmatched' [{(, then collect
    # whatever is being passed in. It works by anchoring to the EOL
    # so we effectively parse backwards.
    #
    # The idea here is to try to "parse" python without actually using
    # tokenization+ast. The RE is anchored to the END of line so we,
    # effectively, are parsing backwards.
    #
    #  The middle character class is basically:
    #    - opening tokens of func|array|dict
    #    - the rest of the main tokens EXCEPT '.'
    #  escaping is done because these seem to tweak the character class.
    #
    #  The last character class is all characters EXCEPT  closing
    #  func|array|dict tokens.
    #
    # The goal is to isolate the last independent statement
    #
    _unmatched_open_component_re = re.compile(r'''
         (
           .+           # match whatever at the beginning
         )
         (
           (
             [[({ =/*+\-%@<>|^\~\!:]
           )
             [^\])}]*
         )
         $
    ''', re.VERBOSE)

    # identify an import statement most generally for speed. Should actually
    # compare if two .startswith() statements is faster -- but extra care
    # would be needed to isolate the '\b' manually
    _check_import_stmt_re = re.compile(r'^(import|from)\b')

    # completly define an re to match any import stamement form (excluding
    # the 'as' clause.
    _import_stmt_re = re.compile(r'''
    ^
    (
        from\s+(\w+)(\.\w+)*\s+import\s+(\w+)(\.\w+)*
      | import\s+(\w+)(\.\w+)*
    )
    ''', re.VERBOSE)

    # attribute matching
    _attrib_re = re.compile(r"(\w+(\.\w+)*)\.(\w*)")

    def __init__(self, namespace=None, subeditor=None):
        """Create a new completer for the command line.

        Completer([namespace]) -> completer instance.

        If unspecified, the default namespace where completions are performed
        is __main__ (technically, __main__.__dict__). Namespaces should be
        given as dictionaries.

        Completer instances should be used as the completion mechanism of
        readline via the set_completer() call:

        readline.set_completer(Completer(my_namespace).complete)
        """

        if namespace and not isinstance(namespace, dict):
            raise TypeError('namespace must be a dictionary')

        # Don't bind to namespace quite yet, but flag whether the user wants a
        # specific namespace or to use __main__.__dict__. This will allow us
        # to bind to __main__.__dict__ at completion time, not now.
        if namespace is None:
            self.use_main_ns = 1
        else:
            self.use_main_ns = 0
            self.namespace = namespace

        # configure the subeditor
        self.subeditor = subeditor

        # holds the matches of the sub-statement being matched
        self.matches = []

    def complete(self, text):
        """Direct completer."""
        if self.use_main_ns:
            self.namespace = __main__.__dict__

        # just in case there is some leading whitespace
        text = text.strip()

        # handle import statements
        if self._check_import_stmt_re.match(text):
            return self.import_matches(text)

        # isolate the components to be completed
        comp_sre = self._unmatched_open_component_re.match(text)

        # assume basic
        token = ''
        close_token = ''
        pretext = ''
        pad = ''
        mtext = text

        # successful match means a complex statement
        if comp_sre:
            pretext = comp_sre.group(1)
            pad = ''  # should grab exact amount of whitespace
            token = comp_sre.group(2)[0]
            mtext = comp_sre.group(2)[1:].strip()
            if len(comp_sre.group(2)) > 1:
                if comp_sre.group(2)[1] in ['"', "'"]:
                    token += comp_sre.group(2)[1]
                    mtext = comp_sre.group(2)[2:].strip()

        # manage the text component needing completion properly
        if token == "['" or token == '["':
            self.matches = self.dict_matches(pretext, mtext)
            close_token = token[1] + ']'
        elif token == '[':
            self.matches = self.array_matches(pretext, mtext)
            close_token = ']'
        elif "." in mtext:
            self.matches = self.attr_matches(mtext)
        else:
            self.matches = self.global_matches(mtext)

        # remember to re-attach the leading text...
        matches = []
        for match in self.matches:
            matches.append(pretext + token + pad + match + close_token)

        # done
        return matches

    @staticmethod
    def _entity_postfix(val, word):
        """Identify types"""
        if isinstance(val, (str, int, float, bytes, bool, complex)):
            pass
        elif isinstance(val, dict):
            word = word + "['"
        elif isinstance(val, (list, set, tuple, range, bytearray, frozenset)):
            word = word + "["
        elif callable(val):
            word = word + "("
        elif hasattr(val, '__class__'):
            word = word + "."
        return word

    def import_matches(self, text):
        """Compute matches when text appears to have an import statement.

        text   - the actual data

        Return a list of all packages and modules available.

        Note, this only does packages and modules... not submodules or other
        symbols.  (It does not "import" or "parse" the module.)  It will
        complete os, sys or ctypes.util because they are dirs/files. It won't
        do
             import os.pa<tab>
        which *could* complete to 'os.path'; os.path is a definition within
        os.py.

        """
        pretext = text
        if ' ' in text:
            pretext = text[:text.rindex(' ') + 1]
        textparts = text.split()

        modulepath = ''
        matches = []

        # filter out 'as' situations
        if 'as' in textparts:
            self.matches = []
            return []

        # collect base package in 'from' cases
        if len(textparts) > 2:
            modulepath = textparts[1]

        # handle (import|from) stuff  cases
        partial = textparts[len(textparts) - 1]
        if modulepath != '':
            partial = modulepath + '.' + partial

        if '.' not in partial:
            for modname in sys.builtin_module_names:
                if modname.startswith(partial):
                    #print("  builtin: " + modname)
                    matches.append(modname)

        #for importer, modname, ispkg in pkgutil.walk_packages(
        for _, modname, _ in pkgutil.walk_packages(
                path=None, onerror=lambda x: None):
            if modname.startswith(partial):
                #print("  check: " + modname)
                if modulepath != '':
                    matches.append(modname[len(modulepath) + 1:])
                else:
                    matches.append(modname)

        # save for later
        self.matches = matches

        # create the full line
        return [pretext + x for x in matches]

    def dict_matches(self, pretext, text):
        """Identify the possible completion keys within a dictionary.

        text is the current estimate of the key-name
        pretext is the (cruft?) + dictionary_name

        Return a list of all matching keys.

        """
        # extract the 'parent' dict object
        dobj = self._isolate_object(pretext)
        if dobj is None:
            return []

        # provide all keys if no estimation
        if text == '':
            results = [k for k in dobj.keys()]
            return results

        # for valid data, match any keys...
        results = [k for k in dobj.keys() if k.startswith(text)]
        return results

    def _isolate_object(self, text):
        """Rummage through text line, extract the parent object text
        and locate the actual object
        """

        # assume all text is relevant
        objtext = text

        # extract the 'parent' object name-text
        comp_sre = self._unmatched_open_component_re.match(text)
        if comp_sre:
            objtext = comp_sre.group(2)[1:]
            if len(objtext) > 0 and objtext[0] in ['"', "'"]:
                objtext = objtext[1:]

        # I'm not a fan of the blind 'eval', but am not sure of a better
        # way to do this
        try:
            pobj = eval(objtext, self.namespace)
        except Exception:
            return None

        return pobj

    def array_matches(self, pretext, text):
        """Identify the available indicies for the array.

        text is the current estimate of the index
        pretext is the (cruft?) + array_name

        Return a list of all index combinations.

        """
        # extract the 'parent' array object
        aobj = self._isolate_object(pretext)
        if aobj is None:
            return []

        # no hints means put out all options... could be a long list
        if text == '':
            return [str(x) for x in range(len(aobj))]

        # implicit info: an array of ZERO length has no completions...
        return [str(x) for x in range(len(aobj)) if str(x).startswith(text)]

    def global_matches(self, text):
        """Compute matches when text is a simple name.

        Return a list of all keywords, built-in functions and names currently
        defined in self.namespace that match.

        """
        matches = []
        seen = {"__builtins__"}
        textn = len(text)
        for word in keyword.kwlist:
            if word[:textn] == text:
                seen.add(word)
                if word in {'finally', 'try'}:
                    word = word + ':'
                elif word not in {
                        'False', 'None', 'True', 'break', 'continue', 'pass',
                        'else'
                }:
                    word = word + ' '
                matches.append(word)
        for nspace in [self.namespace, builtins.__dict__]:
            for word, val in nspace.items():
                if word[:textn] == text and word not in seen:
                    seen.add(word)
                    matches.append(Completer._entity_postfix(val, word))
        return matches

    def attr_matches(self, text):
        """Compute matches when text contains a dot.

        Assuming the text is of the form NAME.NAME....[NAME], and is
        evaluable in self.namespace, it will be evaluated and its attributes
        (as revealed by dir()) are used as possible completions.  (For class
        instances, class members are also considered.)

        WARNING: this can still invoke arbitrary C code, if an object
        with a __getattr__ hook is evaluated.

        """
        attr_sre = self._attrib_re.match(text)
        if not attr_sre:
            return []
        expr, attr = attr_sre.group(1, 3)
        try:
            thisobject = eval(expr, self.namespace)
        except Exception:
            return []

        # get the content of the object, except __builtins__
        words = set(dir(thisobject))
        words.discard("__builtins__")

        if hasattr(thisobject, '__class__'):
            words.add('__class__')
            words.update(self.get_class_members(thisobject.__class__))
        matches = []
        attrn = len(attr)
        if attr == '':
            noprefix = '_'
        elif attr == '_':
            noprefix = '__'
        else:
            noprefix = None
        while True:
            for word in words:
                if (word[:attrn] == attr and
                        not (noprefix and word[:attrn + 1] == noprefix)):
                    match = "%s.%s" % (expr, word)
                    try:
                        val = getattr(thisobject, word)
                    except AttributeError:
                        pass  # Include even if attribute not set
                    else:
                        match = Completer._entity_postfix(val, match)
                    matches.append(match)
            if matches or not noprefix:
                break
            if noprefix == '_':
                noprefix = '__'
            else:
                noprefix = None
        matches.sort()
        return matches

    def get_class_members(self, klass):
        """Thoroughly inspect a given instance to find *all* members"""
        ret = dir(klass)
        if hasattr(klass, '__bases__'):
            for base in klass.__bases__:
                ret = ret + self.get_class_members(base)
        return ret


class ReadlineCompleter(Completer):
    """Readline support for extended completer"""

    def __init__(self, namespace=None):
        try:
            import readline
            import atexit
            super().__init__(namespace, readline)
            readline.set_completer(self.complete)
            # Release references early at shutdown (the readline module's
            # contents are quasi-immortal, and the completer function holds a
            # reference to globals).
            atexit.register(lambda: readline.set_completer(None))
        except ImportError:
            super().__init__(namespace)

    def complete(self, text, state):
        """Return the next possible completion for 'text'.

        This is called successively with state == 0, 1, 2, ... until it
        returns None.  The completion should begin with 'text'.

        Backwards support for readline.
        """
        if self.use_main_ns:
            self.namespace = __main__.__dict__

        if not text.strip():
            if state == 0:
                if self.subeditor:
                    self.subeditor.insert_text('\t')
                    self.subeditor.redisplay()
                    return ''
                else:
                    return '\t'
            else:
                return None

        if state == 0:
            super().complete(text)
        try:
            return self.matches[state]
        except IndexError:
            return None


class EditlineCompleter(Completer):
    """Completion support customized for editline

    Editline (and libedit) use a cleaner interface than readline so it is
    separated out here to keep what little delta from the common base
    separated.
    """

    def __init__(self, subeditor, namespace=None):

        # this *may* cause an ImportError.  Let it propagate...
        import editline

        # make sure the user is using it correctly
        if not isinstance(subeditor, editline.editline):
            raise ValueError("must have subeditor of type editline")

        # proceed with the creation...
        super().__init__(namespace, subeditor)

        # adjust the editor for clarity
        self._default_display_matches = self.subeditor.display_matches
        self.subeditor.display_matches = self.display_matches

        # hook it up
        self.subeditor.completer = self.complete

    def display_matches(self, matches):
        """When editline is used, it will naturally show "whole line matches"
        which are annoying.  This 'override' uses the cached statement matches
        to create better lists of stuff.
        """
        self.subeditor._display_matches(self.matches)
