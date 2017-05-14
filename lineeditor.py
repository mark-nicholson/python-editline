
import builtins
import __main__

import sys
import re
import keyword
import pkgutil

from types import *

__all__ = ["Completer"]

class Completer:

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
    
    def __init__(self, namespace = None, editor_support=None):
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

        # holds the matches of the sub-statement being matched
        self.matches = []

        self.editor_support = editor_support
        if self.editor_support:
            self._default_display_matches = self.editor_support.display_matches
            self.editor_support.display_matches = self.display_matches


    def rl_complete(self, text, state):
        """Return the next possible completion for 'text'.

        This is called successively with state == 0, 1, 2, ... until it
        returns None.  The completion should begin with 'text'.

        Backwards support for readline.
        """
        if self.use_main_ns:
            self.namespace = __main__.__dict__
        
        if not text.strip():
            if state == 0:
                if self.editor_support:
                    editor_support.insert_text('\t')
                    editor_support.redisplay()
                    return ''
                else:
                    return '\t'
            else:
                return None

        if state == 0:
            self.complete(text)
        try:
            return self.matches[state]
        except IndexError:
            return None

    def display_matches(self, matches):
        """When editline is used, it will naturally show "whole line matches"
        which are annoying.  This 'override' uses the cached statement matches
        to create better lists of stuff.
        """
        self.editor_support._display_matches(self.matches)
        
    def complete(self, text):
        """Direct completer."""
        if self.use_main_ns:
            self.namespace = __main__.__dict__

        # just in case there is some leading whitespace
        text = text.strip()

        # handle import statements
        rv = self._check_import_stmt_re.match(text)
        if rv:
            return self.import_matches(text)

        # isolate the components to be completed
        r = self._unmatched_open_component_re.match(text)

        # assume basic
        op = ''
        close_op = ''
        pretext = ''
        pad = ''
        mtext = text

        # successful match means a complex statement
        if r:
            pretext = r.group(1)
            pad = ''   # should grab exact amount of whitespace
            op = r.group(2)[0]
            mtext = r.group(2)[1:].strip()
            if len(r.group(2)) > 1:
                if r.group(2)[1] in [ '"', "'" ]:
                    op += r.group(2)[1]
                    mtext = r.group(2)[2:].strip()

        # manage the text component needing completion properly
        if op == "['" or op == '["':
            self.matches = self.dict_matches(pretext, mtext)
            close_op = op[1] + ']'
        elif op == '[':
            self.matches = self.array_matches(pretext, mtext)  
            close_op = ']'
        elif "." in mtext:
            self.matches = self.attr_matches(mtext)
        else:
            self.matches = self.global_matches(mtext)

        # remember to re-attach the leading text...
        matches = []
        for m in self.matches:
            matches.append( pretext + op + pad + m + close_op )

        # done
        return matches
        
    def _callable_postfix(self, val, word):
        """Identify types"""
        if type(val) in [str,int,float,bytes,bool,complex]:   # plain things
            pass
        elif type(val) is dict:
            word = word + "['"
        elif type(val) in [list,set,tuple,range,bytearray,frozenset]:
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
            pretext = text[:text.rindex(' ')+1]
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
        partial = textparts[len(textparts)-1]
        if modulepath != '':
            partial = modulepath + '.' + partial

        if '.' not in partial:
            for modname in sys.builtin_module_names:
                if modname.startswith(partial):
                    #print("  builtin: " + modname)
                    matches.append(modname)

        for importer, modname, ispkg in pkgutil.walk_packages(path=None, onerror=lambda x: None):
            if modname.startswith(partial):
                #print("  check: " + modname)
                if modulepath != '':
                    matches.append(modname[len(modulepath)+1:])
                else:
                    matches.append(modname)

        # save for later
        self.matches = matches

        # create the full line
        return [ pretext + x for x in matches ]

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
            results = [ k for k in dobj.keys() ]
            return results

        # for valid data, match any keys...
        results = [ k for k in dobj.keys() if k.startswith(text) ]
        return results

    def _isolate_object(self, text):
        """Rummage through text line, extract the parent object text
        and locate the actual object
        """
        
        # assume all text is relevant
        objtext = text
        
        # extract the 'parent' object name-text
        r = self._unmatched_open_component_re.match(text)
        if r:
            objtext = r.group(2)[1:]
            if len(objtext) > 0 and objtext[0] in [ '"', "'" ]:
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
            return [ str(x) for x in range(len(aobj)) ]

        # implicit info: an array of ZERO length has no completions... 
        return [ str(x) for x in range(len(aobj)) if str(x).startswith(text) ]

    def global_matches(self, text):
        """Compute matches when text is a simple name.

        Return a list of all keywords, built-in functions and names currently
        defined in self.namespace that match.

        """
        matches = []
        seen = {"__builtins__"}
        n = len(text)
        for word in keyword.kwlist:
            if word[:n] == text:
                seen.add(word)
                if word in {'finally', 'try'}:
                    word = word + ':'
                elif word not in {'False', 'None', 'True',
                                  'break', 'continue', 'pass',
                                  'else'}:
                    word = word + ' '
                matches.append(word)
        for nspace in [self.namespace, builtins.__dict__]:
            for word, val in nspace.items():
                if word[:n] == text and word not in seen:
                    seen.add(word)
                    matches.append(self._callable_postfix(val, word))
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
        m = self._attrib_re.match(text)
        if not m:
            return []
        expr, attr = m.group(1, 3)
        try:
            thisobject = eval(expr, self.namespace)
        except Exception:
            return []

        # get the content of the object, except __builtins__
        words = set(dir(thisobject))
        words.discard("__builtins__")

        if hasattr(thisobject, '__class__'):
            words.add('__class__')
            words.update(get_class_members(thisobject.__class__))
        matches = []
        n = len(attr)
        if attr == '':
            noprefix = '_'
        elif attr == '_':
            noprefix = '__'
        else:
            noprefix = None
        while True:
            for word in words:
                if (word[:n] == attr and
                    not (noprefix and word[:n+1] == noprefix)):
                    match = "%s.%s" % (expr, word)
                    try:
                        val = getattr(thisobject, word)
                    except Exception:
                        pass  # Include even if attribute not set
                    else:
                        match = self._callable_postfix(val, match)
                    matches.append(match)
            if matches or not noprefix:
                break
            if noprefix == '_':
                noprefix = '__'
            else:
                noprefix = None
        matches.sort()
        return matches

def get_class_members(klass):
    ret = dir(klass)
    if hasattr(klass,'__bases__'):
        for base in klass.__bases__:
            ret = ret + get_class_members(base)
    return ret

