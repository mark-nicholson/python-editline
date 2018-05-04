/* Standard definitions */
#include "Python.h"
#include "structmember.h"
#include <stddef.h>
#include <setjmp.h>
#include <signal.h>
#include <errno.h>
#include <sys/time.h>

#include <histedit.h>

/* backport */
#if PY_VERSION_HEX < 0x03040000
#define PyMem_RawMalloc PyMem_Malloc
#define PyMem_RawFree PyMem_Free
#endif


typedef struct {
    PyObject_HEAD

    /* general params */
    char *name;
    unsigned long signature;
    FILE *fin;
    FILE *fout;
    FILE *ferr;
    PyObject *pyin;
    PyObject *pyout;
    PyObject *pyerr;

    /* infra */
    EditLine  *el;
    Tokenizer *tok;
    History   *hist;
    HistEvent  ev;
    
    PyObject *completer; /* Specify a word completer in Python */
    PyObject *begidx;
    PyObject *endidx;

    char     *prompt;
    char      prompt_esc;
    char     *rprompt;
    char      rprompt_esc;

    char      _debug;
} EditLineObject;

typedef struct {
    PyObject_HEAD

    /* global instance of editline.  Used by 'internal' mechanisms */
    EditLineObject *global_instance;  /* is a PyObject! */

} EditLineModule;

/* module reference */
EditLineModule *editline_module_state = NULL;

/*******************************************************************************
 *
 *              Common Routines
 *
 ******************************************************************************/

static void pel_note(const char *str)
{
    //printf("PEL: %s\n", str); 
}

static PyObject *
encode(PyObject *b)
{
    return PyUnicode_EncodeLocale(b, "surrogateescape");
}

static PyObject *
decode(const char *s)
{
    return PyUnicode_DecodeLocale(s, "surrogateescape");
}

static PyObject *
dump_state(EditLineObject *self, PyObject *noarg);

/* callback triggered from libedit on a completion-char request */
static unsigned char
el_complete(EditLine *el, int ch)
{
    const LineInfo *li = el_line(el);
    EditLineObject *self = NULL;
    int len;
    int rv = CC_REFRESH;

    el_get(el, EL_CLIENTDATA, &self);
    if (self == NULL) {
	printf("el_complete() bad self\n");
	return '\0';   /* should raise exception */
    }

    len = (li->cursor - li->buffer);

    /*fprintf(stderr, "ch = %d", ch);
    fprintf(stderr, "  > li `%.*s_%.*s'\n",
	    (int)(li->cursor - li->buffer), li->buffer,
	    (int)(li->lastchar - 1 - li->cursor),
	    (li->cursor >= li->lastchar) ? "" : li->cursor); */

    Py_XDECREF(self->begidx);
    Py_XDECREF(self->endidx);
    self->begidx = PyLong_FromLong((long) 0);
    self->endidx = PyLong_FromLong((long) (li->cursor - li->buffer));
    
    PyObject *r = NULL, *t;
    char *buf;
    buf = malloc(len + 2);
    strncpy(buf, li->buffer, len);
    buf[len] = '\0';
    buf[len+1] = '\0';
    
    t = decode(buf);
    free(buf);

    /* push up to the main routine in python -- better to manage strings */

#ifdef WITH_THREAD
    PyGILState_STATE gilstate;
    if (self == editline_module_state->global_instance)
	gilstate = PyGILState_Ensure();
#endif

    /* this should call the overridden one too! */
    r = PyObject_CallMethod((PyObject*)self, "_completer", "N", t);

#ifdef WITH_THREAD
    if (self == editline_module_state->global_instance)
	PyGILState_Release(gilstate);
#endif

    if (r == NULL || r == Py_None) {
	rv = CC_ERROR;
	goto error;
    }

    /* should check to be sure it is a long */    
    if (!PyLong_Check(r)) {
	rv = CC_ERROR;
	goto error;
    }

    rv = PyLong_AsLong(r);

    error:
    Py_XDECREF(r);

    return rv;
}

static char *
_prompt(EditLine *el)
{
    int rv;
    EditLineObject *self = NULL;

    rv = el_get(el, EL_CLIENTDATA, &self);

    /* should raise exception or something */
    if (rv < 0 || self == NULL) {
	PyErr_SetString(PyExc_SystemError, "libedit lost clientdata");
	return NULL;
    }

    /* use the internal member */
    return self->prompt;
}

static char *
_rprompt(EditLine *el)
{
    int rv;
    EditLineObject *self = NULL;

    rv = el_get(el, EL_CLIENTDATA, &self);

    /* should raise exception or something */
    if (rv < 0 || self == NULL) {
	PyErr_SetString(PyExc_SystemError, "libedit lost clientdata");
	return NULL;
    }

    /* use the internal member */
    return self->rprompt;
}


/*******************************************************************************
 *
 *              EditLine Object Definition
 *
 ******************************************************************************/

static void
_cleanup_editlineobject(EditLineObject *self)
{
    /* mop up libedit */
    if (self->el)
	el_end(self->el);
    if (self->tok)
	tok_end(self->tok);
    if (self->hist)
	history_end(self->hist);

    /* tidy up the allocated bits */
    if (self->name)
	PyMem_RawFree(self->name);
    if (self->prompt)
	PyMem_RawFree(self->prompt);
    if (self->rprompt)
	PyMem_RawFree(self->rprompt);

    /* manage file-handles? */
    if (self->fin)
	fclose(self->fin);
    if (self->fout)
	fclose(self->fout);
    if (self->ferr)
	fclose(self->ferr);

    /* release my ownership of the I/O refs */
    Py_DECREF(self->pyin);
    Py_DECREF(self->pyout);
    Py_DECREF(self->pyerr);
}

static void
elObj_dealloc(EditLineObject* self)
{
    /* free up resources */
    _cleanup_editlineobject(self);
    
    /* nuke myself */
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static int
elObj_init(EditLineObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *pyfd;
    int fd_in, fd_out, fd_err, rv;
    char *name;

    if (!PyArg_ParseTuple(args, "sOOO", &name,
			  &self->pyin, &self->pyout, &self->pyerr))
	return -1;

    /* need to ensure I own the refs */
    Py_INCREF(self->pyin);
    Py_INCREF(self->pyout);
    Py_INCREF(self->pyerr);

    /* check that there is fileno() on each stream */
    pyfd = PyObject_CallMethod(self->pyin, "fileno", NULL);
    fd_in = (int) PyLong_AsLong(pyfd);
    self->fin = fdopen(fd_in, "r");
    pyfd = PyObject_CallMethod(self->pyout, "fileno", NULL);
    fd_out = (int) PyLong_AsLong(pyfd);
    self->fout = fdopen(fd_out, "w");
    pyfd = PyObject_CallMethod(self->pyerr, "fileno", NULL);
    fd_err = (int) PyLong_AsLong(pyfd);
    self->ferr = fdopen(fd_err, "w");

    //printf("in: %d  out:%d  err:%d\n", fd_in, fd_out, fd_err);

    self->name = PyMem_RawMalloc(strlen(name));
    if (self->name == NULL) {
	PyErr_NoMemory();
	goto error;
    }
    strcpy(self->name, name);

    /* prepare the default prompt */
    #define MY_INIT_PROMPT "EL> "
    self->prompt = PyMem_RawMalloc(strlen(MY_INIT_PROMPT)+1);
    if (self->prompt == NULL) {
	PyErr_NoMemory();
	goto error;
    }
    strcpy(self->prompt, MY_INIT_PROMPT);
    self->prompt_esc = '\1';

    /* prepare the right-prompt to be empty */
    self->rprompt = PyMem_RawMalloc(2);
    if (self->rprompt == NULL) {
	PyErr_NoMemory();
	goto error;
    }
    self->rprompt[0] = '\0';
    self->rprompt[1] = '\0';
    self->rprompt_esc = '\1';

    self->_debug = 0;
    self->signature = 0xDEADBEEFUL;

    /* create the history manager */
    self->hist = history_init();
    if (self->hist == NULL) {
	PyErr_SetString(PyExc_ValueError, "history init failed");
	goto error;
    }

    /* setup the history buffer */
    rv = history(self->hist, &self->ev, H_SETSIZE, 100);
    if (rv < 0) {
	PyErr_SetString(PyExc_ValueError, "setting history size failed");
	goto error;
    }
    rv = history(self->hist, &self->ev, H_SETUNIQUE, 0x1);
    if (rv < 0) {
	PyErr_SetString(PyExc_ValueError, "setting history uniqueness failed");
	goto error;
    }

    /* create the tokenizer */
    self->tok = tok_init(NULL);
    if (self->tok == NULL) {
	PyErr_SetString(PyExc_ValueError, "tokenizer init failed");
	goto error;
    }

    /* create the libedit instance */
    self->el = el_init(name,self->fin, self->fout, self->ferr);
    if (self->el == NULL) {
	PyErr_SetString(PyExc_ValueError, "libedit init failed");
	goto error;
    }

    /* general init ... */
    el_set(self->el, EL_EDITOR, "emacs");
    el_set(self->el, EL_SIGNAL, 1);

    el_set(self->el, EL_PROMPT_ESC, _prompt, self->prompt_esc);
    el_set(self->el, EL_RPROMPT_ESC, _rprompt, self->rprompt_esc);

    el_set(self->el, EL_HIST, history, self->hist);
    
    el_set(self->el, EL_ADDFN, "ed-complete", "Complete argument", el_complete);
    el_set(self->el, EL_BIND, "^I", "ed-complete", NULL);

    el_source(self->el, NULL);

    self->begidx = PyLong_FromLong(0L);
    self->endidx = PyLong_FromLong(0L);

    /* leave myself a breadcrumb... */
    el_set(self->el, EL_CLIENTDATA, self);
    
    return 0;

 error:
    _cleanup_editlineobject(self);
    return -1;
}

static PyMemberDef elObj_members[] = {
    {
	"_debug",
	T_BOOL,
	offsetof(EditLineObject, _debug),
	0,
	"flag for debugging"
    },
    {
	"in_stream",
	T_OBJECT_EX,
	offsetof(EditLineObject, pyin),
	0,
	"I/O stream for terminal input"
    },
    {
	"out_stream",
	T_OBJECT_EX,
	offsetof(EditLineObject, pyout),
	0,
	"I/O stream for terminal output"
    },
    {
	"err_stream",
	T_OBJECT_EX,
	offsetof(EditLineObject, pyerr),
	0,
	"I/O stream for terminal error output"
    },
    {NULL}  /* Sentinel */
};

/* Interrupt handler */

static jmp_buf jbuf;

/* ARGSUSED */
static void
onintr(int sig)
{
    longjmp(jbuf, 1);
}

/*
 * Provides the mechanics of collecting a line from libedit
 * and managing the various supported features of line-completion
 * special commands, ...
 */
static char *
common_line_interaction(EditLineObject *self)
{
    int n, rv, remember = 0;
    char *p;
    const char *buf;
    HistEvent ev;
    PyObject *cmd = NULL;
    PyObject *ncmd = NULL;
    PyObject *method_name;
    
    /* collect the string */
    buf = el_gets(self->el, &n);
    
    /* something went wrong ... not exactly sure how to manage this */
    if (n < 0) {
	if (errno == EINTR) {
	    printf("Snagged by an interrupt s=%d\n", PyErr_CheckSignals());
	}
	else {
	    printf("el_gets choked on: %s\n", strerror(errno));
	}
	el_reset(self->el);
	return (char *) PyErr_SetFromErrno(PyExc_SystemError);
    }

    if (n == 0) {
	/* appears to be when you get ^D or EOF */
	p = PyMem_RawMalloc(1);
        if (p != NULL)
            *p = '\0';
        return p;
    }

    /* valid count returned, but buffer is weird? */
    if (buf == NULL) {
	PyErr_SetString(PyExc_SystemError, "el_gets returned a bad buffer");
	return NULL;
    }

    /* run the custom command interface -- push up to Python code*/
#ifdef WITH_THREAD
    PyGILState_STATE gilstate = PyGILState_Ensure();
#endif

    /* create an object of the buf cmd */
    cmd = Py_BuildValue("s#", buf, n);
    if (cmd == NULL || cmd == Py_None) {
	/* hmm. bad string conversion some how... fight forward...*/
	goto done;
    }

    /* create the method name as a python str */
    method_name = Py_BuildValue("s", "_run_command");

    /* this should call the overridden one too! */
    ncmd = PyObject_CallMethodObjArgs((PyObject*)self, method_name, cmd);

    /* its useful life is over */
    Py_DECREF(method_name);

#ifdef WITH_THREAD
    PyGILState_Release(gilstate);
#endif

    /* a response of None indicates the command is consumed */
    if (ncmd == NULL || ncmd == Py_None) {
	buf = "\n";    /* truncate it to an "empty" */
	n = 1;
	goto done;
    }

    /* is it just the same command we sent? */
    if (ncmd == cmd) {
	remember = 1;
	goto done;
    }
    
    const char *nbuf = NULL;
    int nbuflen = -1;

    /* looks like we got something different back... */
    rv = PyArg_Parse(ncmd, "s#", &nbuf, &nbuflen);
    if (rv < 0) {
	/* hmm. invalid return... cannot assume the command was consumed */
	/* send the original buf to the parser -- come what may */
	goto done;
    }

    /* conversion is successful, move ahead with it */
    buf = nbuf;
    n = nbuflen;
    remember = 1;

    /* create a RawMalloc'd buffer */
 done:
    p = PyMem_RawMalloc(n+1);
    if (p == NULL) {
	PyErr_NoMemory();
	return NULL;
    }
	
    /* Copy the malloc'ed buffer into a PyMem_Malloc'ed one. */
    strncpy(p, buf, n);
    p[n] = '\0';

    /* snoop through the string */
    const char *pp = p;
    while (*pp != '\0') {
	if (isspace(*pp++))
	    continue;
	break;
    }

    /* ignore "whitespace" only lines */
    if (pp == p+n)
	remember = 0;
    
    /* remember cmds, but ignore "empty" lines */
    if (remember && strlen(p) > 0)
	history(self->hist, &ev, H_ENTER, p);

    /* clean up the python objects */
    if (cmd != NULL)
	Py_DECREF(cmd);    /* this one I'm sure of */
    if (ncmd != NULL)
	Py_DECREF(ncmd);   /* this one, not entirely */
    
    return p;
}


/*
 * Python's entry point to this module
 */
static char *
call_editline(FILE *sys_stdin, FILE *sys_stdout, const char *prompt)
{
    char *p;
    PyOS_sighandler_t old_inthandler;
    EditLineObject *el_gi = editline_module_state->global_instance;

    /* init missing... */
    if (el_gi == NULL) {
	PyErr_SetString(PyExc_SystemError, "invalid editline global instance");
	return NULL;
    }

    /* don't do the allocation unless it is different... */
    if (strncmp(prompt, el_gi->prompt, strlen(prompt)) != 0) {
	p = PyMem_RawMalloc(strlen(prompt)+1);
	if (p == NULL) {
	    PyErr_NoMemory();
	    return NULL;
	}
	strcpy(p, prompt);
	if (el_gi->prompt != NULL)
	    PyMem_RawFree(el_gi->prompt);
	el_gi->prompt = p;
    }

    /*
     * this seems like a hack, although it is from readline.c
     * but it gets around a '\n' needed to interpret a ^C signal
     */
    old_inthandler = PyOS_setsig(SIGINT, onintr);
    if (setjmp(jbuf)) {
#ifdef HAVE_SIGRELSE
        /* This seems necessary on SunOS 4.1 (Rasmus Hahn) */
        sigrelse(SIGINT);
#endif
        PyOS_setsig(SIGINT, old_inthandler);
        return NULL;
    }

    /* interact with the user */
    return common_line_interaction(el_gi);
}


/* python ship to manage the completions above 'c' */
static PyObject *
_completer(EditLineObject *self, PyObject *text)
{
    /* force an inherited routine */
    Py_RETURN_NOTIMPLEMENTED;
}
PyDoc_STRVAR(doc__completer,
"_completer() -> None\n\
Handle reducing the options at the python level, not C.");

    
/* get a line from the terminal */
static PyObject *
readline(EditLineObject *self, PyObject *noarg)
{
    const char *buf;

    /* do the interaction */
    buf = common_line_interaction(self);
    if (! buf)
	Py_RETURN_NONE;

    /* pass back what we got */
    return decode(buf);
}
PyDoc_STRVAR(doc_readline,
"readline() -> String\n\
Collect a string from libedit.");


/* pass on command to bind */
static PyObject *
bind(EditLineObject *self, PyObject *keystring, PyObject *cmd)
{
    int rv;
    PyObject *en_key = encode(keystring);
    PyObject *en_cmd = encode(cmd);
    pel_note(__FUNCTION__);
    if (en_key == NULL || en_cmd == NULL) {
        return NULL;
    }
    
    rv = el_set(self->el, EL_BIND,
	   PyBytes_AS_STRING(en_key), PyBytes_AS_STRING(en_cmd));

    Py_DECREF(en_key);
    Py_DECREF(en_cmd);

    return PyLong_FromLong((long)rv);
}
PyDoc_STRVAR(doc_bind,
"bind(string) -> Int\n\
Execute the init line provided in the string argument.");

#if 0
/* emulate the functionality at the python level... */
static PyObject *
parse_and_bind(EditLineObject *self, PyObject *string)
{
    /* ideally, this should be in python code */
    pel_note(__FUNCTION__);
    PyObject_Print(string, stdout, 0);
    Py_RETURN_NONE;
}
PyDoc_STRVAR(doc_parse_and_bind,
"parse_and_bind(string) -> None\n\
Translate readline init line provided in the string argument.");
#endif

static PyObject *
get_line_buffer(EditLineObject *self, PyObject *noarg)
{
    PyObject *pyline;
    const LineInfo *linfo;
    char *s;
    int len;

    pel_note(__FUNCTION__);
    linfo = el_line(self->el); 
    len = linfo->lastchar - linfo->buffer;

    s = PyMem_RawMalloc(len + 1);
    if (s != NULL) {
	strncpy(s, linfo->buffer, len);
	pyline = decode(s);
	PyMem_RawFree(s);
	return pyline;
    }

    /* perhaps return ""? */
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_get_line_buffer,
"get_line_buffer() -> string\n\
return the current contents of the line buffer.");

/* Exported function to insert text into the line buffer */

static PyObject *
insert_text(EditLineObject *self, PyObject *string)
{
    PyObject *encoded = encode(string);
    pel_note(__FUNCTION__);
    if (encoded == NULL) {
        return NULL;
    }
    el_insertstr(self->el, PyBytes_AS_STRING(encoded));
    Py_DECREF(encoded);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_insert_text,
"insert_text(string) -> None\n\
Insert text into the line buffer at the cursor position.");

static PyObject *
delete_text(EditLineObject *self, PyObject *pycount)
{
    const LineInfo *linfo;
    int cur_line_len;
    int count;
    pel_note(__FUNCTION__);

    /* convert the value */
    count = PyLong_AsLong(pycount);
    if (count < 0)
	Py_RETURN_NONE;

    /* get the current line itself */
    linfo = el_line(self->el);
    cur_line_len = linfo->lastchar - linfo->buffer;

    /* value is bogus as it is out of range */
    if (count > cur_line_len)
	Py_RETURN_NONE;

    /* rub out the data */
    el_deletestr(self->el, count);

    /* done */
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_delete_text,
"delete_text(count) -> None\n\
Deletes 'count' characters before the cursor position.");


/* Redisplay the line buffer */

static PyObject *
redisplay(EditLineObject *self, PyObject *noarg)
{
    el_set(self->el, EL_REFRESH);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_redisplay,
"redisplay() -> None\n\
Change what's displayed on the screen to reflect the current\n\
contents of the line buffer.");




/* Exported function to parse a readline init file */

static PyObject *
read_init_file(EditLineObject *self, PyObject *args)
{
    PyObject *filename_obj = Py_None, *filename_bytes;
    
    if (!PyArg_ParseTuple(args, "|O:read_init_file", &filename_obj))
        return NULL;
    
    if (filename_obj == Py_None)
	return NULL;

    if (!PyUnicode_FSConverter(filename_obj, &filename_bytes))
	return NULL;

    errno = el_source(self->el, PyBytes_AsString(filename_bytes));

    Py_DECREF(filename_bytes);
    if (errno)
        return PyErr_SetFromErrno(PyExc_IOError);
    Py_RETURN_NONE;
}

PyDoc_STRVAR(doc_read_init_file,
"read_init_file([filename]) -> None\n\
Execute a readline initialization file.\n\
The default filename is the last filename used.");


/* Exported function to load a readline history file */

static PyObject *
read_history_file(EditLineObject *self, PyObject *args)
{
    int rv;
    PyObject *filename_obj = Py_None, *filename_bytes;
    HistEvent ev;

    if (!PyArg_ParseTuple(args, "|O:read_history_file", &filename_obj))
        return NULL;

    if (filename_obj == Py_None)
	return NULL;

    if (!PyUnicode_FSConverter(filename_obj, &filename_bytes))
	return NULL;

    rv = history(self->hist, &ev, H_LOAD, PyBytes_AsString(filename_bytes));
    Py_DECREF(filename_bytes);

    return PyLong_FromLong((long)rv);
}

PyDoc_STRVAR(doc_read_history_file,
"read_history_file([filename]) -> Int\n\
Load a readline history file.\n\
The default filename is ~/.python_history.");


/* Exported function to save a readline history file */

static PyObject *
write_history_file(EditLineObject *self, PyObject *args)
{
    int rv;
    PyObject *filename_obj = Py_None, *filename_bytes;
    HistEvent ev;
    char *filename;

    if (!PyArg_ParseTuple(args, "|O:write_history_file", &filename_obj))
        return NULL;
    if (filename_obj == Py_None)
	return NULL;

    if (!PyUnicode_FSConverter(filename_obj, &filename_bytes))
	return NULL;

    filename = PyBytes_AsString(filename_bytes);

    rv = history(self->hist, &ev, H_SAVE, filename);
    Py_XDECREF(filename_bytes);

    return PyLong_FromLong((long) rv);
}

PyDoc_STRVAR(doc_write_history_file,
"write_history_file([filename]) -> None\n\
Save a readline history file.\n\
The default filename is ~/.history.");

static PyObject *
add_history_entry(EditLineObject *self, PyObject *cmd)
{
    int rv;
    PyObject *en_cmd = encode(cmd);
    HistEvent ev;
    
    if (en_cmd == NULL) {
        return NULL;
    }

    rv = history(self->hist, &ev, H_ENTER, PyBytes_AS_STRING(en_cmd));

    Py_DECREF(en_cmd);

    return PyLong_FromLong((long)rv);
}
PyDoc_STRVAR(doc_add_history_entry,
"add_history_entry(cmd_str) -> Int\n\
Add a history entry directly.");

/* Exported function to get current length of history */

static PyObject *
get_current_history_length(EditLineObject *self, PyObject *noarg)
{
    HistEvent ev;
    int events;

    events = history(self->hist, &ev, H_GETSIZE);
    
    return PyLong_FromLong((long)events);
}

PyDoc_STRVAR(doc_get_current_history_length,
"get_current_history_length() -> integer\n\
return the current (not the maximum) length of history.");


static PyObject *
_histevent_to_pyobject(HistEvent *ev)
{
    PyObject *ev_num;
    PyObject *ev_str;
    PyObject *tuple;
    
    if (ev == NULL) {
	PyErr_SetString(PyExc_ValueError,
			"Invalid event reference.");
	return NULL;
    }

    /* convert the number */
    ev_num = PyLong_FromLong((long)ev->num);
    if (ev_num == NULL) {
	PyErr_SetString(PyExc_ValueError,
			"Failed to convert ev.num.");
	return NULL;
    }
    //printf("ev_num(0,%ld)\n", Py_REFCNT(ev_num));

    /* convert the string */
    ev_str = decode(ev->str);
    if (ev_num == NULL) {
	PyErr_SetString(PyExc_ValueError,
			"Failed to decode ev.str.");
	Py_DECREF(ev_num);
	return NULL;
    }
    //printf("ev_str(0,%ld)\n", Py_REFCNT(ev_str));

    /* cook up a tuple of the values */
    tuple = PyTuple_Pack(2, ev_num, ev_str);

    //printf("tuple(0,%ld)\n", Py_REFCNT(tuple));
    //printf("ev_num(2,%ld)\n", Py_REFCNT(ev_num));
    //printf("ev_str(2,%ld)\n", Py_REFCNT(ev_str));

    /* I don't keep a reference to these */
    Py_DECREF(ev_num);
    Py_DECREF(ev_str);

    //printf("ev_num(3,%ld)\n", Py_REFCNT(ev_num));
    //printf("ev_str(3,%ld)\n", Py_REFCNT(ev_str));

    /* mark an error if something went south ... */
    if (tuple == NULL) {
	PyErr_SetString(PyExc_ValueError,
			"Failed to create HistEvent tuple.");
	return NULL;
    }

    //printf("tuple(1,%ld)\n", Py_REFCNT(tuple));
    /* done */
    return tuple;
}

static PyObject *
do_history(EditLineObject *self, PyObject *args)
{
    int cmd = -1;
    int int_arg = -1;
    int rv = 0;
    int hval = 0;
    PyObject *obj = NULL;
    HistEvent ev;
    const char *tag = NULL;

    /* use the cmd value to extract the other args */
    if (!PyArg_ParseTuple(args, "i|i", &cmd, &int_arg)) {
	PyErr_SetString(PyExc_TypeError, "Cannot decode the command value.");
	return NULL;
    }

    //printf("do_history(): cmd = %d  int_arg = %d\n", cmd, int_arg);

    switch (cmd) {
	case H_CLEAR:
	    rv = history(self->hist, &ev, H_CLEAR);
	    break;
	
	case H_GETSIZE:
	    rv = history(self->hist, &ev, H_GETSIZE);
	    if (rv >= 0)
		obj = PyLong_FromLong((long)ev.num);
	    break;
	    
	case H_SETSIZE:
	    if (!PyArg_ParseTuple(args, "ii", &cmd, hval)) {
		PyErr_SetString(PyExc_TypeError, "Cannot extract size.");
		return NULL;
	    }
	    rv = history(self->hist, &self->ev, H_SETSIZE, hval);
	    break;

	case H_SET:
	    if (int_arg == -1) {
		PyErr_SetString(PyExc_TypeError, "H_SET argument is invalid.");
		return NULL;
	    }
	    rv = history(self->hist, &self->ev, H_SET, int_arg);
	    break;

	case H_NEXT:
	case H_PREV:
	    rv = history(self->hist, &ev, cmd, NULL);
	    if (rv < 0)
		Py_RETURN_NONE;
	    else
		obj = _histevent_to_pyobject(&ev);
	    break;

	case H_FIRST:
	case H_LAST:
	case H_CURR:
	    rv = history(self->hist, &ev, cmd, NULL);
	    if (rv >= 0)
		obj = _histevent_to_pyobject(&ev);
	    break;

	case H_NEXT_EVENT:
	    tag = "H_NEXT_EVENT";
	    /* fall-through */
	    
	case H_PREV_EVENT:
	    if (tag == NULL)
		tag = "H_PREV_EVENT";

	    if (int_arg == -1) {
		PyErr_Format(PyExc_TypeError, "%s argument is invalid.", tag);
		return NULL;
	    }
	    
	    rv = history(self->hist, &ev, cmd, int_arg);
	    if (rv >= 0)
		obj = _histevent_to_pyobject(&ev);
	    break;
	    
	default:
	    break;
    }

    /* bad things ... */
    if (rv < 0) {
	PyErr_Format(PyExc_ValueError,
		     "Data provided failed in history (%d).", rv);
	return NULL;
    }

    /* pass back nothing */
    if (obj == NULL)
	Py_RETURN_NONE;

    /* return the entity */
    return obj;
}
PyDoc_STRVAR(doc_do_history,
	     "Access libedit history infrastructure\n\n"
	     "Args:\n"
	     "    cmd: (int) history command value (H_* constants)\n"
	     "    param: parameter value relative to cmd.\n\n"
	     "Returns:\n"
	     "    Dependent on `cmd` value\n"
	     );

static PyObject*
_show_history(EditLineObject *self, PyObject *args)
{
    PyErr_SetString(PyExc_NotImplementedError,
		    "Subclass must override this routine.");
    Py_RETURN_NONE;
}
PyDoc_STRVAR(doc__show_history,
	     "display the historic commands");


/* Set the completer function */

static PyObject *
set_completer(EditLineObject *self, PyObject *args)
{
    Py_RETURN_NONE;
    //return set_hook("completer", &self->completer, args);
}

PyDoc_STRVAR(doc_set_completer,
"set_completer([function]) -> None\n\
Set or remove the completer function.\n\
The function is called as function(text, state),\n\
for state in 0, 1, 2, ..., until it returns a non-string.\n\
It should return the next possible completion starting with 'text'.");


static PyObject *
get_completer(EditLineObject *self, PyObject *noargs)
{
    if (self->completer == NULL) {
        Py_RETURN_NONE;
    }
    Py_INCREF(self->completer);
    return self->completer;
}

PyDoc_STRVAR(doc_get_completer,
"get_completer() -> function\n\
\n\
Returns current completer function.");


/* Get the beginning index for the scope of the tab-completion */

static PyObject *
get_begidx(EditLineObject *self, PyObject *noarg)
{
    Py_INCREF(self->begidx);
    return self->begidx;
}

PyDoc_STRVAR(doc_get_begidx,
"get_begidx() -> int\n\
get the beginning index of the completion scope");


/* Get the ending index for the scope of the tab-completion */

static PyObject *
get_endidx(EditLineObject *self, PyObject *noarg)
{
    Py_INCREF(self->endidx);
    return self->endidx;
}

PyDoc_STRVAR(doc_get_endidx,
"get_endidx() -> int\n\
get the ending index of the completion scope");

static PyObject *
gettc(EditLineObject *self, PyObject *op_string)
{
    int rv = -1;
    int value = -1;
    const char * op_cstr;
    PyObject *op_encoded = encode(op_string);

    if (op_encoded == NULL) {
        return NULL;
    }

    op_cstr = PyBytes_AS_STRING(op_encoded);

    rv = el_get(self->el, EL_GETTC, op_cstr, &value);

    Py_DECREF(op_encoded);
    if (rv < 0) {
	Py_RETURN_NONE;
    }

    return PyLong_FromLong((long)value);
}
PyDoc_STRVAR(doc_gettc,
"gettc(op_string) -> int|string|none\n\
get terminal configs");

static PyObject *
dump_state(EditLineObject *self, PyObject *noarg)
{
    printf("EditLineObject '%s' (%p)\n", self->name, self);
    printf("    ->signature:   0x%lx\n", self->signature);
    printf("    ->el:          %p\n", self->el);
    printf("    ->tok:         %p\n", self->tok);
    printf("    ->hist:        %p\n", self->hist);
    printf("    ->prompt:      %s\n", self->prompt);
    printf("    ->prompt_esc:  %d\n", self->prompt_esc);
    printf("    ->rprompt:     %s\n", self->rprompt);
    printf("    ->rprompt_esc: %d\n", self->rprompt_esc);
    printf("    ->_Debug:      %d\n", self->_debug);

    Py_RETURN_NONE;
}
PyDoc_STRVAR(doc_dump_state,
"dump_state() -> None\n\
display internal C stuff");

static PyMethodDef elObj_methods[] = {
    {
	"gettc",
	(PyCFunction) gettc,
	METH_O,
	doc_gettc
    },
    {
	"readline",
	(PyCFunction) readline,
	METH_NOARGS,
	doc_readline
    },
    {
	"_completer",
	(PyCFunction) _completer,
	METH_O,
	doc__completer
    },
    {
	"bind",
	(PyCFunction)bind,
	METH_O,
	doc_bind
    },
#if 0
    {
	"parse_and_bind",
	(PyCFunction)parse_and_bind,
	METH_O,
	doc_parse_and_bind
    },
#endif
    {
	"get_line_buffer",
	(PyCFunction) get_line_buffer,
	METH_NOARGS,
	doc_get_line_buffer
    },
    {
	"insert_text",
	(PyCFunction) insert_text,
	METH_O,
	doc_insert_text
    },
    {
	"delete_text",
	(PyCFunction) delete_text,
	METH_O,
	doc_delete_text
    },
    {
	"redisplay",
	(PyCFunction) redisplay,
	METH_NOARGS,
	doc_redisplay
    },
    {
	"read_init_file",
	(PyCFunction) read_init_file,
	METH_VARARGS,
	doc_read_init_file
    },
    {
	"read_history_file",
	(PyCFunction) read_history_file,
	METH_VARARGS,
	doc_read_history_file
    },
    {
	"write_history_file",
	(PyCFunction) write_history_file,
	METH_VARARGS,
	doc_write_history_file
    },
    {
	"add_history_entry",
	(PyCFunction) add_history_entry,
	METH_O,
	doc_add_history_entry
    },
    {
	"get_current_history_length",
	(PyCFunction) get_current_history_length,
	METH_NOARGS,
	doc_get_current_history_length
    },
    {
	"history",
	(PyCFunction) do_history,
	METH_VARARGS,
	doc_do_history
    },
    {
	"_show_history",
	(PyCFunction) _show_history,
	METH_NOARGS,
	doc__show_history
    },
    {
	"set_completer",
	(PyCFunction) set_completer,
	METH_VARARGS,
	doc_set_completer
    },
    {
	"get_completer",
	(PyCFunction) get_completer,
	METH_NOARGS,
	doc_get_completer
    },
    {
	"get_begidx",
	(PyCFunction) get_begidx,
	METH_NOARGS,
	doc_get_begidx
    },
    {
	"get_endidx",
	(PyCFunction) get_endidx,
	METH_NOARGS,
	doc_get_endidx
    },
    {
	"dump_state",
	(PyCFunction) dump_state,
	METH_NOARGS,
	doc_dump_state
    },
    {NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyObject*
elObj_prompt_getter(EditLineObject *self, void* closure)
{
    return decode(self->prompt);
}

static int
elObj_prompt_setter(EditLineObject *self, PyObject *value, void *closure)
{
    int rv = 0;
    int n;
    char *new_prompt;
    const char *encoded_c;
    PyObject *encoded;
    
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the prompt attribute");
        return -1;
    }

    if (! PyUnicode_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "The prompt attribute value must be a string");
        return -1;
    }

    /* it is stored as a C string */
    encoded = encode(value);
    if (encoded == NULL) {
        PyErr_SetString(PyExc_ValueError,
                        "The prompt attribute could not be encoded");
        return -1;
    }

    /* get it as a c-string */
    encoded_c = PyBytes_AS_STRING(encoded);
    n = strlen(encoded_c);

    /* create a RawMalloc'd buffer */
    new_prompt = PyMem_RawMalloc(n+1);
    if (new_prompt == NULL) {
	Py_DECREF(encoded);
	PyErr_NoMemory();
	return -1;
    }

    /* Copy the malloc'ed buffer into a PyMem_Malloc'ed one. */
    strncpy(new_prompt, encoded_c, n);
    new_prompt[n] = '\0';

    /* release the previous one if it was assigned */
    if (self->prompt)
	PyMem_RawFree(self->prompt);

    /* make this the active one */
    self->prompt = new_prompt;

    /*
     * REFs:  only manage 'enc' to ensure it gets removed.  We don't 'own'
     *        any of the others, so we just borrow the ref.
     */
    Py_DECREF(encoded);

    /* done */
    return rv;
}

#if 0
static PyObject*
elObj_prompt_esc_getter(EditLineObject *self, void* closure)
{
    return decode(self->prompt_esc);
}
#endif


static PyObject*
elObj_rprompt_getter(EditLineObject *self, void* closure)
{
    return decode(self->rprompt);
}

static int
elObj_rprompt_setter(EditLineObject *self, PyObject *value, void *closure)
{
    int rv = 0;
    int n;
    char *new_rprompt;
    const char *encoded_c;
    PyObject *encoded;
    
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the rprompt attribute");
        return -1;
    }

    if (! PyUnicode_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "The rprompt attribute value must be a string");
        return -1;
    }

    /* it is stored as a C string */
    encoded = encode(value);
    if (encoded == NULL) {
        PyErr_SetString(PyExc_ValueError,
                        "The rprompt attribute could not be encoded");
        return -1;
    }

    /* get it as a c-string */
    encoded_c = PyBytes_AS_STRING(encoded);
    n = strlen(encoded_c);

    /* create a RawMalloc'd buffer */
    new_rprompt = PyMem_RawMalloc(n+1);
    if (new_rprompt == NULL) {
	Py_DECREF(encoded);
	PyErr_NoMemory();
	return -1;
    }

    /* Copy the malloc'ed buffer into a PyMem_Malloc'ed one. */
    strncpy(new_rprompt, encoded_c, n);
    new_rprompt[n] = '\0';

    /* release the previous one if it was assigned */
    if (self->rprompt)
	PyMem_RawFree(self->rprompt);

    /* make this the active one */
    self->rprompt = new_rprompt;

    /*
     * REFs:  only manage 'enc' to ensure it gets removed.  We don't 'own'
     *        any of the others, so we just borrow the ref.
     */
    Py_DECREF(encoded);

    /* done */
    return rv;
}

#define HISTORY_GETSET_GETTER_MACRO(tag)	\
    { \
      # tag, \
      (getter) tag ## _getter, \
      NULL, \
      doc_ ## tag, \
      NULL \
    }
    
#define HISTORY_FN_MACRO(tag) \
    static PyObject* \
    tag ## _getter(EditLineObject *self, void *closure) \
    { return PyLong_FromLong(tag); } \
    PyDoc_STRVAR(doc_ ## tag, \
		 "history() command value " # tag );

/* functions to create the values in the object */
HISTORY_FN_MACRO(H_SETSIZE)
HISTORY_FN_MACRO(H_GETSIZE)
HISTORY_FN_MACRO(H_FIRST)
HISTORY_FN_MACRO(H_LAST)
HISTORY_FN_MACRO(H_PREV)
HISTORY_FN_MACRO(H_NEXT)
HISTORY_FN_MACRO(H_CURR)
HISTORY_FN_MACRO(H_ADD)
HISTORY_FN_MACRO(H_APPEND)
HISTORY_FN_MACRO(H_ENTER)
HISTORY_FN_MACRO(H_SET)
HISTORY_FN_MACRO(H_PREV_STR)
HISTORY_FN_MACRO(H_NEXT_STR)
HISTORY_FN_MACRO(H_PREV_EVENT)
HISTORY_FN_MACRO(H_NEXT_EVENT)
HISTORY_FN_MACRO(H_LOAD)
HISTORY_FN_MACRO(H_SAVE)
HISTORY_FN_MACRO(H_SETUNIQUE)
HISTORY_FN_MACRO(H_GETUNIQUE)
HISTORY_FN_MACRO(H_DEL)


static PyGetSetDef EditLineType_getseters[] = {
    {
	"prompt",
	(getter)elObj_prompt_getter,
	(setter)elObj_prompt_setter,
	"Configure the prompt string",
	NULL
    },
    {
	"rprompt",
	(getter)elObj_rprompt_getter,
	(setter)elObj_rprompt_setter,
	"Configure the right-side prompt string",
	NULL
    },
    
    HISTORY_GETSET_GETTER_MACRO(H_SETSIZE),
    HISTORY_GETSET_GETTER_MACRO(H_GETSIZE),
    HISTORY_GETSET_GETTER_MACRO(H_FIRST),
    HISTORY_GETSET_GETTER_MACRO(H_LAST),
    HISTORY_GETSET_GETTER_MACRO(H_PREV),
    HISTORY_GETSET_GETTER_MACRO(H_NEXT),
    HISTORY_GETSET_GETTER_MACRO(H_CURR),
    HISTORY_GETSET_GETTER_MACRO(H_ADD),
    HISTORY_GETSET_GETTER_MACRO(H_APPEND),
    HISTORY_GETSET_GETTER_MACRO(H_ENTER),
    HISTORY_GETSET_GETTER_MACRO(H_SET),
    HISTORY_GETSET_GETTER_MACRO(H_PREV_STR),
    HISTORY_GETSET_GETTER_MACRO(H_NEXT_STR),
    HISTORY_GETSET_GETTER_MACRO(H_PREV_EVENT),
    HISTORY_GETSET_GETTER_MACRO(H_NEXT_EVENT),
    HISTORY_GETSET_GETTER_MACRO(H_LOAD),
    HISTORY_GETSET_GETTER_MACRO(H_SAVE),
    HISTORY_GETSET_GETTER_MACRO(H_SETUNIQUE),
    HISTORY_GETSET_GETTER_MACRO(H_GETUNIQUE),
    HISTORY_GETSET_GETTER_MACRO(H_DEL),
    
    {NULL, NULL, NULL, NULL, NULL}  /* Sentinel */
};

static PyTypeObject EditLineType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "editline.EditLineBase",   /* tp_name */
    sizeof(EditLineObject),    /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)elObj_dealloc, /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,        /* tp_flags */
    "EditLineBase objects",    /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    elObj_methods,             /* tp_methods */
    elObj_members,             /* tp_members */
    EditLineType_getseters,    /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)elObj_init,      /* tp_init */
    PyType_GenericAlloc,       /* tp_alloc */
    PyType_GenericNew,         /* tp_new */
    PyObject_Del,              /* tp_free */
};


/*******************************************************************************
 *
 *                 Module Definitions
 *
 ******************************************************************************/

#define get_editline_module_state(o) ((EditLineModule *)PyModule_GetState(o))

static int
editline_clear(PyObject *m)
{
    EditLineModule *state = get_editline_module_state(m);
    Py_CLEAR(state->global_instance);

    return 0;
}

static int
editline_traverse(PyObject *m, visitproc visit, void *arg)
{
    EditLineModule *state = get_editline_module_state(m);
    Py_VISIT(state->global_instance);
    return 0;
}

static void
editline_free(void *m)
{
    /* close down the references */
    editline_clear((PyObject *)m);
}

static PyObject *
set_global_instance(void *m, PyObject *gi)
{
    EditLineModule *state = get_editline_module_state(m);

    if (editline_module_state != state)
	editline_module_state = state;
    
    if (gi != NULL) {
	state->global_instance = (EditLineObject*)gi;
	Py_INCREF(state->global_instance);
	PyOS_ReadlineFunctionPointer = call_editline;
    }
    else {
	PyOS_ReadlineFunctionPointer = NULL;
	Py_DECREF(state->global_instance);
	state->global_instance = NULL;
    }
    
    Py_RETURN_NONE;
}
PyDoc_STRVAR(doc_set_global_instance,
"Register the reference to the global editline (system) instance.");

static PyObject *
get_global_instance(void *m, PyObject *none)
{
    EditLineModule *state = get_editline_module_state(m);

    if (state->global_instance == NULL)
	Py_RETURN_NONE;

    /* we still own it, no ref inc */
    return (PyObject*) state->global_instance;
}
PyDoc_STRVAR(doc_get_global_instance,
"Provide the reference to the global editline (system) instance.");


/* Table of functions exported by the module */

static struct PyMethodDef editline_methods[] =
{
    {
	"set_global_instance",
	(PyCFunction) set_global_instance,
	METH_O,
	doc_set_global_instance
    },
    {
	"get_global_instance",
	(PyCFunction) get_global_instance,
	METH_NOARGS,
	doc_get_global_instance
    },
    {0, 0}
};



/* Initialize the module */

PyDoc_STRVAR(doc_module,
"Importing this module enables command line editing using libedit.");

static struct PyModuleDef el_module = {
    PyModuleDef_HEAD_INIT,
    "_editline",
    doc_module,
    sizeof(EditLineModule),
    editline_methods,
    NULL,
    editline_traverse,
    editline_clear,
    editline_free
};

PyMODINIT_FUNC
PyInit__editline(void)
{
    PyObject *m;
    char buf[32];

    if (PyType_Ready(&EditLineType) < 0)
        return NULL;
    
    m = PyModule_Create(&el_module);
    if (m == NULL)
        return NULL;

    /* remember the module */
    editline_module_state = get_editline_module_state(m);

    /* versioning info */
#if defined(LIBEDIT_MAJOR) && defined(LIBEDIT_MINOR) 
    snprintf(buf, 32, "%d.%d", LIBEDIT_MAJOR, LIBEDIT_MINOR);
#else
    /* FreeBSD's histedit.h lacks version info */
    snprintf(buf, 32, "%d.%d", 9, 9);
#endif
    PyModule_AddStringConstant(m, "_VERSION", buf);

    /* create the function return params */
    PyModule_AddIntConstant(m, "CC_NORM", CC_NORM);
    PyModule_AddIntConstant(m, "CC_NEWLINE", CC_NEWLINE);
    PyModule_AddIntConstant(m, "CC_EOF", CC_EOF);
    PyModule_AddIntConstant(m, "CC_ARGHACK", CC_ARGHACK);
    PyModule_AddIntConstant(m, "CC_REFRESH", CC_REFRESH);
    PyModule_AddIntConstant(m, "CC_REFRESH_BEEP", CC_REFRESH_BEEP);
    PyModule_AddIntConstant(m, "CC_CURSOR", CC_CURSOR);
    PyModule_AddIntConstant(m, "CC_REDISPLAY", CC_REDISPLAY);
    PyModule_AddIntConstant(m, "CC_ERROR", CC_ERROR);
    PyModule_AddIntConstant(m, "CC_FATAL", CC_FATAL);

    /* initialize the type */
    Py_INCREF(&EditLineType);
    PyModule_AddObject(m, "EditLineBase", (PyObject *)&EditLineType);

    /* done */
    return m;
}
