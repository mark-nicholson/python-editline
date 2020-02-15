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

__all__ = ["Completer", "ReadlineCompleter",
           "EditlineCompleter", "global_line_editor"]

def _debug(tag, *args):
    """Debugging utility.

    Args:
        tag:  debug tag to enable/disable visibility
        args: va-args of what to print

    Returns:
       Nothing

    """
    do_debug = False
    if not do_debug:
        return
    monitor_tags = [
        #'complete(0)',
        #'complete(match)',
        #'attr_matches'
        #'global_matches',
        #'dict_matches',
        #'array_matches'
        #'LastExpr(0)',
        #'LastExpr(1)',
        #'LastExpr(2)',
        #'LastExpr(3)',
        #'LastExpr(4)',
        #'LastExpr(5)',
        #'LastExpr(6)',
        #'LastExpr(7)',
        #'LastExpr(8)'
    ]
    if tag in monitor_tags:
        print(os.linesep + "DBG["+tag+"]:", *args)


#
# Maintain a global for the lineditor
#
_gle_data = None

def global_line_editor(gle=None):
    """Access the global lineeditor instance.

    Args:
        gle: (optional) new global lineeditor instance

    Returns:
        Current global lineeditor instance

    """
    global _gle_data
    if gle is not None:
        _gle_data = gle
    return _gle_data


class Completer(object):
    """General tab-completion support for underlying terminal infrastructure.

    Provides extended tab-completion mechanisms in a way which is available
    to both 'readline' and 'editline'. The goal is to coalece the completion
    functionality into a single place and have it independent of one specific
    terminal library's interface.

    Args:
        subeditor: An instance of editline or readline to implement
                           the basic terminal interface.
        namespace: (optional): The namespace to use for completion.
                              If unspecified, the default namespace where
                              completions are performed is __main__
                              (technically, __main__.__dict__).

    """

    allow_eval_of_calls = False
    """(bool) - Flag to allow evals of function calls within
    leading expressions.  Careful when this is True!

    """

    # matches single AND double quoted 'strings' in text. It will do so even
    # to support any escaped single and double quotes
    _str_dq_re = re.compile(r'''
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

    def __init__(self, subeditor: object, namespace: dict = None) -> object:
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


    def complete(self, text: str) -> list:
        """Command completion routine.

        Args:
            text: The current (full) command-line, containing probably
                  incomplete syntax.

        Returns:
            A list of strings (possibly empty) of the possible matches which
            would provide valid syntax.

        """
        if self.use_main_ns:
            self.namespace = __main__.__dict__

        # handle import statements
        if self._check_import_stmt_re.match(text.strip()):
            return self._import_matches(text.strip())

        # chop up the line
        pretext, expr2c, token, pad, mtext = self._extract_parts(text)
        _debug('complete(0)',
               'pt=|{0}| ex=|{1}| tk=|{2}| pad=|{3}| mt=|{4}|'
               .format(pretext, expr2c, token, pad, mtext))

        # assume basic
        close_token = ''

        # manage the text component needing completion properly
        if token.startswith('['):

            # extract the 'parent' object
            obj = self._eval_to_object(expr2c)
            if obj is None:
                return []     # no object implies no completions

            # what sort of thing is this
            flavour = Completer._estimate_flavour(obj)

            # handle it based on the flavour
            if flavour == 'dict-ish':   # could have incomplete syntax for dict

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
                self.matches = self._dict_matches(obj, mtext)

                # make sure the 'pad' is in between the [ and the '
                if pad != '':
                    token = token[0] + pad + token[1]
                    pad = ''

            # check for list-ish objs and anything call with [ that
            #  has __getitem__ is fair
            elif flavour == 'list-ish':
                self.matches = self._array_matches(obj, mtext)
                close_token = ']'

            elif flavour == 'set-ish':
                # invalid syntax...
                token = ''
                close_token = ''
                # automatically delete the index-data and the [ in the buffer
                self.subeditor.delete_text(len(mtext)+1)
                # replace it with '.'
                self.subeditor.insert_text('.')

            else:
                # hmm. something wonky...
                pass

        elif "." in expr2c:
            self.matches = self._attr_matches(expr2c)
            expr2c = ''  # rub this out so the full-line match is clean
        elif expr2c == '':
            # here, there is no expression, but unterminated text
            self.matches = self._global_matches(mtext)
        else:
            self.matches = self._global_matches(expr2c)
            expr2c = ''  # rub this out so the full-line match is clean

        # remember to re-attach the leading text...
        matches = []
        for match in self.matches:
            _debug('complete(match)', pretext + expr2c + token + pad + match + close_token)
            matches.append(pretext + expr2c + token + pad + match + close_token)

        # done
        return matches


    @classmethod
    def _estimate_flavour(cls, obj: object) -> str:
        """Determine a general behaviour of the object.

        Given the object, the goal is to figure out if it is more like a
        list, set, dictionary or something else.

        Args:
            cls: class reference
            obj: An object reference to check

        Returns:
            A string value, one of:
               'list-ish', 'dict-ish', 'set-ish' or 'unknown'
        """

        # easy ones first
        if isinstance(obj, dict):
            return 'dict-ish'
        if isinstance(obj, (list, tuple, range)):
            return 'list-ish'
        if isinstance(obj, (set, frozenset)):
            return 'set-ish'

        # could be either an array or a dict, depends on
        #   what key-type it likes...
        if hasattr(obj, '__getitem__'):
            # start with dictionary key...
            try:
                _ = obj['__Zz_Really-Unlykely-KeY_3.14159']
            except KeyError:
                return 'dict-ish'
            except TypeError:
                # appears not to be a dictionary
                pass

            # ok, now try it as a list
            try:
                _ = obj[2305843009213693951]   # Mersenne Prime #9 (2**61 -1)
            except IndexError:
                return 'list-ish'
            except TypeError:
                # dunno, sets do this, but they would get
                #   filtered by not having __getitem__
                return 'unknown'

        # ?!?!
        return 'unknown'


    @classmethod
    def _entity_postfix(cls, val, word: str) -> str:
        """Append relevant syntax string to indicate `val`'s type.

        Args:
            cls:  class reference
            val:  an object who's syntax is defined in `word`
            word: the text which evaluates to `val`

        Returns:
            Pass back `word`, potentially appended with appropriate syntax
            in order to be recognizable as a certain type.

        """
        flavour = cls._estimate_flavour(val)

        if isinstance(val, (str, int, float, bytes, bool, complex)):
            pass
        elif flavour == 'dict-ish':   # isinstance(val, dict):
            word = word + "['"
        elif flavour == 'list-ish':   #isinstance(val, (list, tuple, range, bytearray)):
            word = word + "["
        elif flavour == 'set-ish':    #isinstance(val, (set, frozenset)):
            pass   # acts basically like an object or attr, no indexing
        elif callable(val):
            word = word + "("
        elif hasattr(val, '__class__'):
            word = word + "."
        return word


    @classmethod
    def _expr_has_call(cls, text: str) ->  bool:
        '''Inspect text and determine if it contains `call` syntax.

        Args:
            cls: class reference
            text:  a python expression (in code form)

        Returns:
            True if the expression would evaluate a callable
            False if not

        '''
        opens = text.count('(')
        closes = text.count(')')

        if closes > 0 and opens >= closes:
            return True
        return False


    def _eval_to_object(self, expr: str) -> object:
        """Convert the text in the argument into a python object.

        This is, generally, a dangerous thing to do as it is more or less
        evaluating totally unsafe code.  Alas...

        Args:
            expr: python syntax describing which object as source code

        Returns:
            The runtime object found by `eval` of the `expr` argument or None.

        Notes:
            This routine is affected by the `allow_eval_of_calls` flag. By
            default, it *will not* eval source code which would enact an
            (arbitrary) callable.  The flag can be altered to change this
            behaviour and let circumstances fall in the lap of the user.

        """
        # need to check if there is a "call" in the expression
        if Completer._expr_has_call(expr):
            if not self.allow_eval_of_calls:
                _debug('_eval_to_object', "Blocking call eval")
                return None

        # I'm not a fan of the blind 'eval', but am not sure of a better
        # way to do this
        try:
            pobj = eval(expr, self.namespace)
        except Exception:
            return None
        return pobj


    def _import_matches(self, text: str) -> list:
        """Compute matches when text appears to have an import statement.

        Args:
            text: python code for the import statement

        Returns:
            Names of all packages and modules available which match.

        Notes:
            This only does packages and modules... not submodules or other
            symbols.  (It does not "import" or "parse" the module.)  It will
            complete os, sys or ctypes.util because they are dirs/files. It
            won't do

                import os.pa<tab>

            which *could* complete to 'os.path'; os.path is a definition
            within os.py.

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


    @classmethod
    def _dict_matches(cls, dobj: dict, text: str) -> list:
        """Identify the possible completion keys within a dictionary.

        Args:
            dobj: the dictionary whose keys are to be checked
            text: some or no text forming the start of the key to be matched

        Returns:
            All keys which match the prefix given.

        """
        _debug('dict_matches', text)
        # provide all keys if no estimation
        if text == '':
            results = [k for k in dobj.keys()]
            return results

        # for valid data, match any keys...
        results = [k for k in dobj.keys() if k.startswith(text)]
        return results


    @classmethod
    def _array_matches(cls, aobj: list, text: str) -> list:
        """Identify the possible completion indices within a list.

        Args:
            aobj: the list whose keys are to be checked
            text: some or no text forming the start of the index to be matched

        Returns:
            All indicies which match the prefix given. Strings of integers, not
            integers themselves are returned.

        """
        _debug('array_matches', text)
        # no hints means put out all options... could be a long list
        if text is None or text == '':
            return [str(x) for x in range(len(aobj))]

        # implicit info: an array of ZERO length has no completions...
        return [str(x) for x in range(len(aobj)) if str(x).startswith(text)]


    def _global_matches(self, text: str) -> list:
        """Compute matches within the global namespace.

        Args:
            text: initial characters of the global entity name to match

        Returns:
            All keywords, built-in functions and names currently
            defined in self.namespace that match the given prefix text.

        """
        _debug('global_matches', text)
        matches = []
        seen = {"__builtins__"}
        textn = len(text)
        for word in keyword.kwlist:
            if word[:textn] == text:
                seen.add(word)
                if word in ['finally', 'try']:
                    word = word + ':'
                elif word not in ['False', 'None', 'True', 'break',
                                  'continue', 'pass', 'else']:
                    word = word + ' '
                matches.append(word)
        for nspace in [self.namespace, builtins.__dict__]:
            for word, val in nspace.items():
                if word[:textn] == text and word not in seen:
                    seen.add(word)
                    matches.append(Completer._entity_postfix(val, word))
        return matches


    def _attr_matches(self, text: str) -> list:
        """Compute matching attributes to an object.

        Args:
            text: expression, containing a '.' and some or no characters of
                  the attribute desired

        Returns:
            All attribute names (as strings) which are found within the
            parent object.

        Notes:
            Assuming the text is of the form NAME.NAME....[NAME], and is
            evaluable in self.namespace, it will be evaluated and its attributes
            (as revealed by dir()) are used as possible completions.  (For class
            instances, class members are also considered.)

        Warnings:
            This can still invoke arbitrary C code, if an object
            with a __getattr__ hook is evaluated.

        """
        # bust apart the trailing item from the base object
        (expr, attr) = text.rsplit('.', 1)

        _debug('attr_matches', 'expr={0} attr={1}'.format(expr, attr))

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
            words.update(self._get_class_members(pobj.__class__))
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
                    except Exception:
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


    @classmethod
    def _get_class_members(cls, item: object) -> list:
        """Thoroughly inspect a given instance to find *all* members.

        Args:
            cls:  class reference
            item: the object or base-class to inspect

        Returns:
            A list of the attributes found in the object and all of its
            base classes.

        """
        ret = dir(item)
        if hasattr(item, '__bases__'):
            for base in item.__bases__:
                ret = ret + cls._get_class_members(base)
        return ret


    @classmethod
    def _last_expr(cls, text: str) -> (str, str):
        """Separate the last-expression and the pre-text.

        Args:
            cls:  reference to the Completer class
            text: a full line of python code

        Returns:
            A tuple of the pretext and the last (possibly incomplete)
            expression.

        """
        nesting = 0
        for index, char in enumerate(reversed(text)):
            if char in ")]}":
                nesting += 1
            elif nesting:
                if char in "([{":
                    nesting -= 1
            elif char in ' \t\n`~!@#$%^&*-=+\\|;:,<>[](){}/?':
                return text[:-index], text[-index:]
        return '', text


    @classmethod
    def _string_sub(cls, text: str) -> (str, dict):
        """Substitute any python string syntax with a simple token.

        Args:
            cls:  class reference
            text: a line of python code

        Returns:
            2-Tuple of the original string with string-syntax items replaced
            plus a mapping of the inserted (unique) tokens to the original
            strings.

        Notes:
            Supports all stringifiers in Python: single and double quotes
            along with their triple counterparts.

        """
        rtv = ''
        idx = 0
        done = False
        cache = {}

        while not done:

            # do a basic search to find anything
            mrv = cls._str_dq_re.search(text)
            if mrv is None:
                # we're done, pass back the safe-str and stats
                return text, cache

            # we've got a match

            # create a substitution token
            sstr = '___PyEl_{:d}'.format(idx)

            # remember which token is supposed to be which string
            cache[sstr] = mrv.group()

            # switch it out
            rtv = cls._str_dq_re.sub(sstr, text, 1)
            if rtv == text:
                break
            text = rtv
            idx += 1

        # no luck
        return text, {}


    def _extract_parts(self, text: str) -> (str, str, str, str, str):
        """Parse a line of python code (... without the parser).

        Args:
            text:  line of python source code

        Returns:
            5-Tuple
               pretext          - any leading code not involved
               expr-to-complete - the expression which will be completed
               lookup_token     - possible lookup token ([ or [' or [")
               padding          - possible whitespace between token and str
               unterminated_str - the fragment of code to be expanded

        Notes:
            Just about any of the tuple entries can be empty. This routine
            is more like a semi-parser/semi-tokenizer.  It is the parent
            level code which will have to sort out the *meaning* of each
            entry as to how the overall cmd is structured.

        """
        # replace all quoted strings with simpler tokens.  This avoid
        # confusing later stages of the parsing by finding python tokens
        # embedded in data-strings.
        pretext, cache = self._string_sub(text[:])
        #_debug("    ", pretext)
        #_debug("    ", cache)

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

        #_debug('LastExpr(0)',
        #      'pt >{0}<   uts >{1}<'.format(pretext, unterm_str))

        # declare this and assume there is none
        lookup_tok = None

        # handle possible whitespace at the end of the string
        pt_rstr = pretext.rstrip()            # ws is stuck on pretext
        padding = pretext[len(pt_rstr):]      # separate the pad chars
        pretext = pt_rstr                     # move forward with clean pretext
        #_debug('LastExpr(1)',
        #      'pt >{0}<  pad >{1}<  uts >{2}<'.format(pretext,
        #                                              padding, unterm_str))

        # figure out the last expression
        pretext, expr2c = self._last_expr(pretext)
        #_debug('LastExpr(2)', 'pt >{0}<   expr2c >{1}<'.format(pretext, expr2c))

        # handle possible whitespace between the expr or [ and the match-text
        if padding == '':
            pt_rstr = pretext.rstrip()        # ws is stuck on pretext
            padding = pretext[len(pt_rstr):]  # separate the pad chars
            pretext = pt_rstr                 # move forward with clean pretext

        #_debug('LastExpr(3)',
        #      'pt >{0}<  pad >{1}<  expr2c >{2}<'.format(pretext,
        #                                                 padding, expr2c))

        # check expr2c to see if it looks like a number.
        #     (Probably could expand it to support more number formats...
        if unterm_str is None and expr2c.isnumeric():
            unterm_str = expr2c
            pretext, expr2c = self._last_expr(pretext)

        #_debug('LastExpr(4)',
        #      'pt >{0}<   expr2c >{1}<'.format(pretext, expr2c))

        # is the ending part now an array or dictionary lookup?
        if expr2c.endswith('['):
            _debug('LastExpr(5)', "Array or Dictionary ending")
            lookup_tok = '['
            if pretext == '':
                pretext, expr2c = self._last_expr(expr2c[:-len(lookup_tok)])

            #_debug('LastExpr(6)',
            #      'pt >{0}<   expr2c >{1}<'.format(pretext, expr2c))

            # shift the start string char to the bracket
            if unterm_str is not None:
                if unterm_str[0] in "'\"":
                    lookup_tok += unterm_str[0]
                    unterm_str = unterm_str[1:]


        # handle primitive cases where there is just a global function call
        if pretext == '' and expr2c.endswith('('):
            pretext = expr2c
            expr2c = ''

        #_debug('LastExpr(7)',
        #      'base-expr: |{0}  lookup: |{1}|'.format(expr2c,lookup_tok))

        # recheck pretext and expr2c to replace the cache-string-token(s)
        for key, value in cache.items():
            if key in expr2c:
                expr2c = expr2c.replace(key, value)
            if key in pretext:
                pretext = pretext.replace(key, value)

        _debug('LastExpr(8)', "Final Base Expression: " + expr2c)

        # tidy up the Nones...
        if unterm_str is None:
            unterm_str = ''
        if lookup_tok is None:
            lookup_tok = ''

        # done
        return pretext, expr2c, lookup_tok, padding, unterm_str


class ReadlineCompleter(Completer):
    """Readline support for extended completer

    Args:
        subeditor: An instance of editline or readline to implement
                           the basic terminal interface.
        namespace: (optional): The namespace to use for completion.
                              If unspecified, the default namespace where
                              completions are performed is __main__
                              (technically, __main__.__dict__).

    """

    def __init__(self, namespace=None):
        try:
            import readline
            import atexit
            super().__init__(namespace, readline)
            readline.set_completer(self.rl_complete)
            # Release references early at shutdown (the readline module's
            # contents are quasi-immortal, and the completer function holds a
            # reference to globals).
            atexit.register(lambda: readline.set_completer(None))
        except ImportError:
            super().__init__(namespace)


    def rl_complete(self, text: str, state: int) -> int:
        """Return the next possible completion state for 'text'.

        This is called successively with state == 0, 1, 2, ... until it
        returns None.  The completion should begin with 'text'.

        Args:
            text:  python code line
            state: which matches are best

        Returns:
            The next state value.

        Notes:
            Backward support for readline.  This has not been tested
            particularly thoroughly.

        """
        if self.use_main_ns:
            self.namespace = __main__.__dict__

        if not text.strip():
            if state == 0:
                if self.subeditor:
                    self.subeditor.insert_text('\t')
                    self.subeditor.redisplay()
                    return ''
                return '\t'
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

    Args:
        subeditor: An instance of editline or readline to implement
                           the basic terminal interface.
        namespace: (optional): The namespace to use for completion.
                              If unspecified, the default namespace where
                              completions are performed is __main__
                              (technically, __main__.__dict__).

    """

    def __init__(self, subeditor, namespace: dict = None):

        # this *may* cause an ImportError.  Let it propagate...
        import editline

        # make sure the user is using it correctly
        if not isinstance(subeditor, editline.editline.EditLine):
            raise ValueError("must have subeditor of type EditLine")

        # proceed with the creation...
        super().__init__(subeditor, namespace)

        # adjust the editor for clarity
        self._default_display_matches = self.subeditor.display_matches
        self.subeditor.display_matches = self.display_matches

        # hook it up
        self.subeditor.completer = self.complete


    def display_matches(self, matches: list):
        """Display relevant information for each match value.

        When editline is used, it will naturally show "whole line matches"
        which are annoying.  This 'override' uses the cached statement matches
        to create better lists of stuff.

        Args:
            matches: the list of matches which contain the full-text matches

        """
        self.subeditor._display_matches(self.matches)
