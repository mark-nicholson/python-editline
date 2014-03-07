#
# cython: c_string_type=str, c_string_encoding=ascii
#
#  Cython binding to libedit.so
#

#cimport editline.histedit as histedit
cimport histedit

from libc.stdio cimport *
from libc.string cimport *
from libc.stdlib cimport *

from cpython.object cimport *
from cpython.string cimport *


#
#  This is a genear routine to call a Python callable
#
## cdef char * _old_global_prompt_thunk(histedit.EditLine *el):
##     cdef char *rv
##     cdef EditLine pel
##     cdef void *ptr
##     cdef object pstr

##     # extract the custom data (the Python EditLine class)
##     histedit.el_get(el, histedit.EL_CLIENTDATA, &ptr)
##     pel = <EditLine> ptr
    
##     # call the function
##     pstr = pel._prompt_fn()
##     if pstr is None:
##         print("Failed to get a valid prompt obj")
##         raise ValueError("Failed to set a prompt")
    
##     # return the resultant string
##     rv = <char*> pstr
##     return rv

#
#  This is a general routine to call a Python callable
#
## cdef char * _old_global_rprompt_thunk(histedit.EditLine *el):
##     cdef char *rv
##     cdef EditLine pel
##     cdef void *ptr
##     cdef object pstr

##     # extract the custom data (the Python EditLine class)
##     histedit.el_get(el, histedit.EL_CLIENTDATA, &ptr)
##     pel = <EditLine> ptr
    
##     # call the function
##     pstr = pel._rprompt_fn()
##     if pstr is None:
##         print("Failed to get a valid rprompt obj")
##         raise ValueError("Failed to set an rprompt")
    
##     # return the resultant string
##     rv = <char*> pstr
##     return rv

class PyLineInfo(object):
    pass

class HistEdit(object):
    CC_NORM = histedit.CC_NORM
    CC_NEWLINE = histedit.CC_NEWLINE
    CC_EOF = histedit.CC_EOF
    CC_ARGHACK = histedit.CC_ARGHACK
    CC_REFRESH = histedit.CC_REFRESH
    CC_CURSOR = histedit.CC_CURSOR
    CC_ERROR = histedit.CC_ERROR
    CC_FATAL = histedit.CC_FATAL
    CC_REDISPLAY = histedit.CC_REDISPLAY
    CC_REFRESH_BEEP = histedit.CC_REFRESH_BEEP

#
#  This is a general routine to call a Python callable registered as 'name'
#
cdef object _common_thunk(histedit.EditLine *el, char *name):
    cdef EditLine pel
    cdef void *ptr
    cdef object callback

    # extract the custom data (the Python EditLine class)
    histedit.el_get(el, histedit.EL_CLIENTDATA, &ptr)
    pel = <EditLine> ptr

    # check it
    if name not in pel._fns:
        raise ValueError("function name '%s' is not registered" % name)

    # grab it
    callback = pel._fns[name]
    if callback is None:
        raise ValueError("function '%s' has no callable" % name)
    
    # call the function
    return callback()

# select the prompt routine
cdef char * _global_prompt_thunk(histedit.EditLine *el):
    cdef object rv
    rv = _common_thunk(el, 'prompt')
    return <char *>rv

# select the rprompt routine
cdef char * _global_rprompt_thunk(histedit.EditLine *el):
    cdef object rv
    rv = _common_thunk(el, 'rprompt')
    return <char *>rv

# select the completer routine
cdef unsigned char _global_completer_thunk(histedit.EditLine *el, int ch):
    cdef EditLine pel
    cdef void *ptr
    cdef object callback
    cdef object rv
    cdef char *line
    cdef int   state

    name = 'ed-complete'
    
    # extract the custom data (the Python EditLine class)
    histedit.el_get(el, histedit.EL_CLIENTDATA, &ptr)
    pel = <EditLine> ptr

    # check it
    if name not in pel._fns:
        raise ValueError("function name '%s' is not registered" % name)

    # grab it
    callback = pel._fns[name]
    if callback is None:
        raise ValueError("function '%s' has no callable" % name)
    
    # call the function
    rv = callback(pel, ch)
    return <int> rv


cdef class EditLine:
    cdef histedit.EditLine * _el
    cdef histedit.History  *_hist
    cdef object             _name
    cdef char               _prompt_esc
    cdef char               _rprompt_esc
    cdef char              *_terminal
    cdef char              *_editor
    cdef object             _fns
    
    def __cinit__(self):
        self._el = NULL
        self._name = None
        self._prompt_esc = 0
        self._rprompt_esc = 0
        self._terminal = NULL
        self._editor = NULL

    def __init__(self, name):
        self._name  = name

        cdef histedit.HistEvent ev
        cdef char *token
        cdef char *fnname
        cdef char *comment

        # setup the function dict
        self._fns = dict()
        self._fns['prompt'] = self._default_prompt
        self._fns['rprompt'] = self._default_rprompt
        self._fns['ed-complete'] = EditLine._default_complete

        # construct a libedit instance
        self._el = histedit.el_init(name, stdin, stdout, stderr)
        if self._el is NULL:
            raise MemoryError()

        # setup the history support
        self._hist = histedit.history_init()
        if self._hist is NULL:
            raise MemoryError()

        # init the basic size
        histedit.history(self._hist, &ev, histedit.H_SETSIZE, 100)

        # register the default history routine with our instance
        histedit.el_set(self._el, histedit.EL_HIST, histedit.history, self._hist)

        print("__init__", self)

        # register this class as 'clientdata'
        histedit.el_set(self._el, histedit.EL_CLIENTDATA, <void*>self)

        # register the prompt thunk
        histedit.el_set(self._el, histedit.EL_PROMPT, &_global_prompt_thunk)

        # register the rprompt thunk
        histedit.el_set(self._el, histedit.EL_RPROMPT, &_global_rprompt_thunk)

        # register the completer thunk
        fnname = 'ed-complete'
        comment = 'complete argument'
        histedit.el_set(self._el, histedit.EL_ADDFN,
                        fnname, comment, &_global_completer_thunk)

        # make 'tab' call the completer
        token = '\x09'
        fnname = 'ed-complete'
        histedit.el_set(self._el, histedit.EL_BIND, token, fnname, NULL)


    def __dealloc__(self):
        print("Deallocating _el")
        if self._el is not NULL:
            histedit.el_end(self._el)
        if self._hist is not NULL:
            histedit.history_end(self._hist)

    def reset(self):
        histedit.el_reset(self._el)


    def gets(self):
        cdef const char *s
        cdef char *tmp_s
        cdef int count
        cdef object item
        s = histedit.el_gets(self._el, &count)
        tmp_s = <char *> malloc(count + 1)
        if tmp_s is NULL:
            raise MemoryError()
        strncpy(tmp_s, s, count)
        tmp_s[count] = '\0'
        item = tmp_s
        free(tmp_s)
        return item

    def getc(self):
        cdef int rv
        cdef char ch
        rv = histedit.el_getc(self._el, &ch)
        if (rv < 0):
            raise IOError()
        return ch

    def line(self):
        li = histedit.el_line(self._el)
        pli = PyLineInfo()
        pli.buffer = li.buffer
        pli.cursor = <int> (li.cursor - li.buffer)
        pli.lastchar = <int> (li.lastchar - li.buffer)
        return pli

    def push(self, s):
        histedit.el_push(self._el, s)

    def beep(self):
        histedit.el_beep(self._el)

    #def parse(self, slist):
    #    histedit.el_parse(self._el, len(slist), slist)

    def show(self):
        print("EL_PROMPT = %d" % histedit.EL_PROMPT)
        print("EL_TERMINAL = %d" % histedit.EL_TERMINAL)
        print("EL_EDITOR = %d" % histedit.EL_EDITOR)
        print("EL_SIGNAL = %d" % histedit.EL_SIGNAL)
        print("EL_BIND = %d" % histedit.EL_BIND)

    #
    #  Completer support
    #
    def _default_complete(self, cur_char):
        print("in _dc:  '%d'" % cur_char)
        return ''

    def completer(self, fn=None):
        old = self._fns['ed-complete']
        if fn is not None:
            self._fns['ed-complete'] = fn
        return old

    # export a 'compliant' API
    get_completer = completer
    set_completer = completer


    #
    #  Manage the (Left) Prompt
    #
    
    def _default_prompt(self):
        return "EL> "
    
    def prompt(self, fn=None):
        old = self._fns['prompt']
        if fn is not None:
            self._fns['prompt'] = fn
        return old

    def prompt_esc(self, esc=None):
        old = self._prompt_esc
        if esc is not None:
            self._prompt_esc = <char>esc
            histedit.el_set(self._el, histedit.EL_PROMPT_ESC,
                            &_global_prompt_thunk, self._prompt_esc)
        return old

    #
    #  Manage the Right-Prompt
    #

    def _default_rprompt(self):
        #return ''
        return " <REL"

    def rprompt(self, fn=None):
        old = self._fns['rprompt']
        if fn is not None:
            self._fns['rprompt'] = fn
        return old

    def rprompt_esc(self, esc=None):
        old = self._rprompt_esc
        if esc is not None:
            self._rprompt_esc = <char>esc
            histedit.el_set(self._el, histedit.EL_RPROMPT_ESC,
                            &_global_rprompt_thunk, self._rprompt_esc)
        return old


    cdef _set_get_int(self, int cmd, object data):
        cdef int rv
        cdef int v

        # pull the underlying value
        if (data is None):
            rv = histedit.el_get(self._el, cmd, &v)
            if rv != 0:
                return None
            return v

        # write it to the underlying lib
        v = data
        rv = histedit.el_set(self._el, cmd, v)
        if rv != 0:
            return None
        return v

    def signal(self, id=None):
        return self._set_get_int(histedit.EL_SIGNAL, id)

    def editmode(self, mode=None):
        return self._set_get_int(histedit.EL_EDITMODE, mode)

    def unbuffered(self, mode=None):
        return self._set_get_int(histedit.EL_UNBUFFERED, mode)

    def prep_term(self, flag):
        return self._set_get_int(histedit.EL_PREP_TERM, flag)

    
    cdef _set_get_str(self, int cmd, char **ref, object data):
        """
        Basic routine for doing el_set with a single char* arg.
        """
        
        cdef int rv
        cdef char *ptr
        cdef char *nptr
        cdef char *lib_str

        # pull the underlying value
        rv = histedit.el_get(self._el, cmd, &lib_str)
        if rv != 0:
            return None

        printf("A: ref    = %p (%s)\n", ref[0], ref[0]);
        printf("A: libstr = %p (%s)\n", lib_str, lib_str);

        # op=read and cached copy matches the one in the library:  all good
        if (data is None) and (ref[0] == lib_str):
            return ref[0]

        # do we need to write data?
        #     a. a write is requested
        #     b. the cached value is unset
        if (data is not None) or (ref[0] == NULL):

            # select the appropriate source string
            ptr = lib_str
            if (data is not None):
                ptr = data

            # make a new (dynamic) str
            nptr = strdup(ptr)

            # write it to the underlying lib
            rv = histedit.el_set(self._el, cmd, nptr)
            if rv != 0:
                return None

            # update the cache
            if (ref[0] != NULL):
                free(ref[0])
            ref[0] = nptr
            
        # *ref is accurate
        return ref[0]

    def terminal(self, term=None):
        return self._set_get_str(histedit.EL_TERMINAL, &self._terminal, term)
    
    def editor(self, editor=None):
        return self._set_get_str(histedit.EL_EDITOR, &self._editor, editor)

    def source(self, fname):
        cdef int rv
        rv = histedit.el_source(self._el, <char*>fname)
        return rv

    def resize(self):
        histedit.el_resize(self._el)

    def insertstr(self, s_ins):
        cdef int rv
        rv = histedit.el_insertstr(self._el, <char*>s_ins)
        return rv

    def deletestr(self, count):
        histedit.el_deletestr(self._el, <int>count)


#
#  Implement a History interface
#
cdef class History:
    cdef histedit.History      *_hist
    cdef int                    _max_size
    
    def __cinit__(self):
        self._hist = NULL
        #self._cev = NULL
        self._max_size = -1

    def __init__(self):
        self._hist = histedit.history_init()
        if self._hist is NULL:
            raise MemoryError()

    def __dealloc__(self):
        if self._hist is not NULL:
            histedit.history_end(self._hist)

    def __len__(self):
        cdef int size
        cdef int rv
        cdef histedit.HistEvent ev
        rv = histedit.history(self._hist, &ev, histedit.H_GETSIZE, &size)
        if rv < 0:
            # should extract fail data from ev
            raise ValueError("Failed to get size")
        return size

    def set_size(self, len):
        cdef int size = len
        cdef int rv
        cdef histedit.HistEvent ev
        rv = histedit.history(self._hist, &ev, histedit.H_SETSIZE, size)
        if rv < 0:
            # should extract fail data from ev
            raise ValueError("Failed to set size")

    def __getitem__(self, idx):
        pass

    def __setitem__(self, idx, value):
        cdef char *s = value
        cdef int rv
        cdef histedit.HistEvent ev
        rv = histedit.history(self._hist, &ev, histedit.H_ENTER, s)
        if rv < 0:
            # should extract fail data from ev
            raise ValueError("Failed to get size")

    def __delitem__(self, key):
        pass

    def __iter__(self):
        pass

    def __reversed__(self):
        pass

    def __contains__(self, a):
        pass

    #
    # List Interface
    #

    def append(self, value):
        cdef int rv
        cdef char *cmd = value
        cdef histedit.HistEvent ev
        rv = histedit.history(self._hist, &ev, histedit.H_ENTER, cmd)
        if rv < 0:
            # should extract fail data from ev
            raise ValueError("Failed to append the new command")
        return ev

    def count(self, value):
        pass

    def extend(self, List):
        for item in List:
            self.append(item)

    def index(self, value):
        pass

    def insert(self, i, x):
        pass

    def pop(self, i=None):
        pass

    def remove(self, x):
        pass

    def reverse(self):
        pass

    #def sort(self):
    #    pass

    def clear(self):
        cdef int rv
        cdef histedit.HistEvent ev
        rv = histedit.history(self._hist, &ev, histedit.H_CLEAR)
        if rv < 0:
            # should extract fail data from ev
            raise ValueError("Failed to clear history")


    def current(self, idx=None):
        cdef int rv
        cdef int c_idx = idx
        cdef histedit.HistEvent ev
        if idx is None:
            rv = histedit.history(self._hist, &ev, histedit.H_CURR)
        else:
            rv = histedit.history(self._hist, &ev, histedit.H_SET, c_idx)
        if rv < 0:
            # should extract fail data from ev
            raise ValueError("Failed to locate current entry")
        return ev

    def unique(self, state=None):
        cdef int rv
        cdef int c_state = state
        cdef histedit.HistEvent ev
        if state is None:
            rv = histedit.history(self._hist, &ev, histedit.H_GETUNIQUE)
        else:
            rv = histedit.history(self._hist, &ev, histedit.H_SETUNIQUE, c_state)
        return rv

    
# done
