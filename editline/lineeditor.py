"""
Comprehensive command line completer support

Provides extended tab-completions support for
    - std items: keywords, attributes
    - import statements
    - array indicies
    - dict keys

It is based on the code from rlcompleter, then pimped out.
"""

import os
import sys
import re
import keyword
import pkgutil

import builtins
import __main__

__all__ = ["Completer", "ReadlineCompleter", "EditlineCompleter", "global_completer"]

# hook to store the global completer for access
global_completer = None

def debug(tag, *args):
    monitor_tags = [
        #'complete(0)',
        #'attr_matches'
        #'global_matches',
        #'dict_matches',
        #'array_matches'
        #'LastExpr(0)',
        #'LastExpr(1)',
        #'LastExpr(2)'
    ]
    if tag in monitor_tags:
        print(os.linesep + "DBG["+tag+"]:", *args)

class Completer:
    """Tab-Completion Support

    Provides extended tab-completion mechanisms in a way which is available
    to both 'readline' and 'editline'.
    """

    # flag to allow evals of function calls -- careful using this when True!
    allow_eval_of_calls = False

    # matches single AND double quoted 'strings' in text. It will do so even
    # to support any escaped single and double quotes
    str_dq_re = re.compile(r'''
        (?<!\\)    # not preceded by a backslash
        ("|\')     # a literal double-quote
        .*?        # 1-or-more characters
        (?<!\\)    # not preceded by a backslash
        \1         # a literal double-quote
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

        # handle import statements
        if self._check_import_stmt_re.match(text.strip()):
            return self.import_matches(text.strip())

        # chop up the line
        pretext, expr2c, token, pad, mtext = self.extract_parts(text)
        debug('complete(0)', 'pt=|{0}| ex=|{1}| tk=|{2}| pad=|{3}| mt=|{4}|'.format(pretext, expr2c, token, pad, mtext))

        # assume basic
        close_token = ''

        # manage the text component needing completion properly
        if token.startswith('['):

            # extract the 'parent' object
            obj = self._eval_to_object(expr2c)
            if obj is None:
                return []     # no object implies no completions

            # handle it based on the type -- could have incomplete syntax for dict
            if isinstance(obj,dict):

                # verify we have *correct* dictionary syntax
                if len(token) < 2:
                    token = token + "'"         # user tabbed at only the [
                    close_token = "']"
                elif 4 >= len(token) > 2:
                    # some sort of use with triple quotes?  Legal, but odd.
                    close_token = token[1] + ']'
                else:
                    close_token = token[1] + ']'

                # figure out what keys are needed..
                self.matches = self.dict_matches(obj, mtext)

            # check for list-ish objs and anything call with [ that has __getitem__ is fair
            elif isinstance(obj,(list,range)) or hasattr(obj,'__getitem__'):
                self.matches = self.array_matches(obj, mtext)
                close_token = ']'

            elif isinstance(obj,(set,frozenset)):
                # invalid syntax...  
                token = ''
                close_token = ''
                # automatically delete the index-data and the [ in the buffer
                self.subeditor.delete_text(len(mtext)+1)
                # replace it with '.'
                self.subeditor.insert_text('.')
                
        elif "." in expr2c:
            self.matches = self.attr_matches(expr2c)
            expr2c = ''  # rub this out so the full-line match is clean
        elif expr2c == '':
            # here, there is no expression, but unterminated text
            self.matches = self.global_matches(mtext)
        else:
            self.matches = self.global_matches(expr2c)
            expr2c = ''  # rub this out so the full-line match is clean

        # remember to re-attach the leading text...
        matches = []
        for match in self.matches:
            #debug('complete(match)', pretext + expr2c + token + match + close_token)
            matches.append(pretext + expr2c + token + pad + match + close_token)

        # done
        return matches

    @staticmethod
    def _entity_postfix(val, word):
        """Identify types"""
        if isinstance(val, (str, int, float, bytes, bool, complex)):
            pass
        elif isinstance(val, dict):
            word = word + "['"
        elif isinstance(val, (list, tuple, range, bytearray)):
            word = word + "["
        elif isinstance(val, (set, frozenset)):
            pass   # acts basically like an object or attr, no indexing
        elif callable(val):
            word = word + "("
        elif hasattr(val, '__class__'):
            word = word + "."
        return word

    def _expr_has_call(self, text):
        '''Snoop through the expr-text and figure out if there is a (...) call'''
        opens = text.count('(')
        closes = text.count(')')

        #debug('_expr_has_call', 'opens={0:d} closes={1:d}'.format(opens, closes))

        if closes > 0 and opens >= closes:
            return True
        return False

    def _eval_to_object(self, expr):
        # need to check if there is a "call" in the expression
        if self._expr_has_call(expr):
            if not self.allow_eval_of_calls:
                debug('_eval_to_object', "Blocking call eval")
                return None
        
        # I'm not a fan of the blind 'eval', but am not sure of a better
        # way to do this
        try:
            pobj = eval(expr, self.namespace)
        except Exception:
            return None
        return pobj

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

    def dict_matches(self, dobj, text):
        """Identify the possible completion keys within a dictionary.

        text: the current estimate of the key-name
        expr: the pre-parsed text-name of the object in question

        Return a list of all matching keys.

        """
        debug('dict_matches', text)
        # provide all keys if no estimation
        if text == '':
            results = [k for k in dobj.keys()]
            return results

        # for valid data, match any keys...
        results = [k for k in dobj.keys() if k.startswith(text)]
        return results

    def array_matches(self, aobj, text):
        """Identify the available indicies for the array.

        text: is the current estimate of the index
        expr: the pre-parsed text-name of the list-object in question

        Return a list of all index combinations.

        """
        debug('array_matches', text)
        # no hints means put out all options... could be a long list
        if text is None or text == '':
            return [str(x) for x in range(len(aobj))]

        # implicit info: an array of ZERO length has no completions...
        return [str(x) for x in range(len(aobj)) if str(x).startswith(text)]

    def global_matches(self, text):
        """Compute matches when text is a simple name.

        Return a list of all keywords, built-in functions and names currently
        defined in self.namespace that match.

        """
        debug('global_matches', text)
        matches = []
        seen = {"__builtins__"}
        textn = len(text)
        for word in keyword.kwlist:
            if word[:textn] == text:
                seen.add(word)
                if word in ['finally', 'try']:
                    word = word + ':'
                elif word not in ['False', 'None', 'True', 'break',
                                  'continue', 'pass','else']:
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
        # bust apart the trailing item from the base object
        (expr,attr) = text.rsplit('.', 1)

        debug('attr_matches', 'expr={0} attr={1}'.format(expr,attr))

        # try to convert it to a parent object
        pobj = self._eval_to_object(expr)

        # did not resolve to an object
        if pobj is None:
            return []

        # get the content of the object, except __builtins__
        words = set(dir(pobj))
        words.discard("__builtins__")

        if hasattr(pobj, '__class__'):
            words.add('__class__')
            words.update(self.get_class_members(pobj.__class__))
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
                        val = getattr(pobj, word)
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


    def _last_expr(self, text):
        '''Chisle through the text and separate the last-expression 
           and the pre-text'''
        nesting = 0
        for index, c in enumerate(reversed(text)):
            if c in ")]}":
                nesting += 1
            elif nesting:
                if c in "([{":
                    nesting -= 1
            elif c in ' \t\n`~!@#$%^&*-=+\\|;:,<>[](){}/?':
                return text[:-index],text[-index:]
        return '',text

    def string_sub(self, text):
        '''Take a string with Python code in it and replace any quoted string
           with a generic (unique) token (... as if it were a variable). Create
           a cache to remember the token <-> real string mapping
           '''
        rv = ''
        idx = 0
        done = False
        cache = {}

        while not done:

            # do a basic search to find anything
            mrv = self.str_dq_re.search(text)
            if mrv is None:
                # we're done, pass back the safe-str and stats
                return text, cache

            # we've got a match

            # create a substitution token
            sstr = '___PyEl_{:d}'.format(idx)

            # remember which token is supposed to be which string
            cache[sstr] = mrv.group()

            # switch it out
            rv = self.str_dq_re.sub(sstr, text, 1)
            if rv == text:
                break
            text = rv
            idx += 1

        # no luck
        return text, {}

    def extract_parts(self, text):
        '''Given a line of python code (likely incomplete), break it up into 
           parts which reflect the way the interpreter needs it to do a 
           sensible completion

        text: string:  line of python code

        Returns:
            pretext : the beginning text unused in the completion 
            expr-to-complete : the expression which would be queried for 
            furthur data lookup-token : None or "[" for lists or "['" for 
            dictionaries unterminated-data : None or whatever partial data is
            relevant
         '''

        # replace all quoted strings with simpler tokens.  This avoid
        # confusing later stages of the parsing by finding python tokens
        # embedded in data-strings.
        pretext, cache = self.string_sub(text[:])
        debug("    ", pretext)
        debug("    ", cache)

        # check if there are any quotes left...
        #       if so, then there is an un-terminated str
        unterm_str = None
        if "'" in pretext:
            idx = pretext.index("'")
            unterm_str = pretext[idx:]
            pretext = pretext[:idx]
        elif '"' in pretext:
            idx = pretext.index('"')
            unterm_str = pretext[idx:]
            pretext = pretext[:idx]

        debug('LastExpr(0)', 'pt >{0}<   uts >{1}<'.format(pretext, unterm_str))


        # declare this and assume there is none
        lookup_tok = None

        # handle possible whitespace at the end of the string
        pt_rstr = pretext.rstrip()                  # ws is stuck on pretext
        padding = pretext[len(pt_rstr):]            # separate the pad chars
        pretext = pt_rstr                           # move forward with clean pretext
        debug('LastExpr(0)', 'pt >{0}<  pad >{1}<  uts >{2}<'.format(pretext, padding, unterm_str))

        # figure out the last expression
        pretext,expr2c = self._last_expr(pretext)
        debug('LastExpr(1)', 'pt >{0}<   expr2c >{1}<'.format(pretext, expr2c))

        # handle possible whitespace between the expr or [ and the match-text
        pt_rstr = pretext.rstrip()                  # ws is stuck on pretext
        padding = pretext[len(pt_rstr):]            # separate the pad chars
        pretext = pt_rstr                           # move forward with clean pretext
        debug('LastExpr(1)', 'pt >{0}<   expr2c >{1}<'.format(pretext, expr2c))

        # check expr2c to see if it looks like a number.
        #     (Probably could expand it to support more number formats...
        if unterm_str is None and expr2c.isnumeric():
            unterm_str = expr2c
            pretext,expr2c = self._last_expr(pretext)

        debug('LastExpr(2)', 'pt >{0}<   expr2c >{1}<'.format(pretext, expr2c))

        # is the ending part now an array or dictionary lookup?
        if expr2c.endswith('['):
            debug('LastExpr(3)', "Array or Dictionary ending")
            lookup_tok = '['
            if pretext == '':
                pretext,expr2c = self._last_expr(expr2c[:-len(lookup_tok)])
            debug('LastExpr(4)', 'pt >{0}<   expr2c >{1}<'.format(pretext, expr2c))

            # shift the start string char to the bracket
            if unterm_str is not None:
                if unterm_str[0] in "'\"":
                    lookup_tok += unterm_str[0]
                    unterm_str = unterm_str[1:]


        # handle primitive cases where there is just a global function call
        if pretext == '' and expr2c.endswith('('):
            pretext = expr2c
            expr2c = ''

        debug('LastExpr(5)', 'base-expr: |{0}  lookup: |{1}|'.format(expr2c,lookup_tok))

        # recheck pretext and expr2c to replace the cache-string-token(s)
        for k,v in cache.items():
            if k in expr2c:
                expr2c = expr2c.replace(k, v)
            if k in pretext:
                pretext = pretext.replace(k, v)

        debug('LastExpr(6)', "Final Base Expression: " + expr2c)

        # tidy up the Nones...
        if unterm_str is None:
            unterm_str = ''
        if lookup_tok is None:
            lookup_tok = ''

        # done:  pretext, expr-to-complete, lookup-token, padding, unterminated-data
        return pretext, expr2c, lookup_tok, padding, unterm_str


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
        if not isinstance(subeditor, editline.editline.editline):
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
