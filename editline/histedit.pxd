#
# file: histedit.pxd
#

from libc.stdio cimport FILE
#cimport libc.stdlib

cdef extern from "histedit.h":

    ctypedef struct EditLine:
        pass

    ctypedef struct LineInfo:
        pass

    enum FnReturnCodes:
        CC_NORM,
        CC_NEWLINE,
        CC_EOF,
        CC_ARGHACK,
        CC_REFRESH,
        CC_CURSOR,
        CC_ERROR,
        CC_FATAL,
        CC_REDISPLAY,
        CC_REFRESH_BEEP

    EditLine*   el_init(const char *name,  \
                        FILE* sys_stdin, FILE *sys_stdout, FILE*sys_stderr)
    EditLine*   el_init_fd(const char *name,  \
                           FILE* sys_stdin, FILE *sys_stdout, FILE*sys_stderr, \
                           int fd_stdin, int fd_stdout, int fd_stderr)
    void        el_end(EditLine *el)
    void        el_reset(EditLine *el)
                
    const char* el_gets(EditLine *el, int *count)
    int         el_getc(EditLine *el, char *buf)
    void        el_push(EditLine *el, const char *str)
    
    void        el_beep(EditLine *el)

    int         el_parse(EditLine *el, int argc, const char **argv)

    int         el_get(EditLine *el, int code, ...)
    int         el_set(EditLine *el, int code, ...)
    unsigned char _el_fn_complete(EditLine *el, int n)

    enum OperationCodes:
        EL_PROMPT = 0,
        EL_TERMINAL,
        EL_EDITOR,
        EL_SIGNAL,
        EL_BIND,
        EL_TELLTC,
        EL_SETTC,
        EL_ECHOTC,
        EL_SETTY,
        EL_ADDFN,
        EL_HIST,
        EL_EDITMODE,
        EL_RPROMPT,
        EL_GETCFN,
        EL_CLIENTDATA,
        EL_UNBUFFERED,
        EL_PREP_TERM,
        EL_GETTC,
        EL_GETFP,
        EL_SETFP,
        EL_REFRESH,
        EL_PROMPT_ESC,
        EL_RPROMPT_ESC,
        EL_RESIZE

    int         el_source(EditLine *el, const char *fname)

    void        el_resize(EditLine *el)

    const LineInfo* el_line(EditLine *el)
    int         el_insertstr(EditLine *el, const char *str)
    void        el_deletestr(EditLine *el, int n)


    #
    #   History Support
    #

    ctypedef struct History:
        pass

    ctypedef struct HistEvent:
        pass


    History*    history_init()
    void        history_end(History* hist)

    int         history(History *hist, HistEvent *ev, int code, ...)

    enum HistoryCode:
        H_FUNC,
        H_SETSIZE,
        H_GETSIZE,
        H_FIRST,
        H_LAST,
        H_PREV,
        H_NEXT,
        H_CURR,
        H_SET,
        H_ADD,
        H_ENTER,
        H_APPEND
        H_END,
        H_NEXT_STR,
        H_PREV_STR,
        H_NEXT_EVENT,
        H_PREV_EVENT,
        H_LOAD,
        H_SAVE,
        H_CLEAR,
        H_SETUNIQUE,
        H_GETUNIQUE,
        H_DEL,
        H_NEXT_EVDATA,
        H_DELDATA,
        H_REPLACE


    #
    #  Tokenization
    #

    ctypedef struct Tokenizer:
        pass
                #
    Tokenizer*   tok_init(const char *str)
    void         tok_end(Tokenizer *tok)
    void         tok_reset(Tokenizer *tok)
    int          tok_line(Tokenizer *tok, const LineInfo *line,
                          int *n, const char ***items, int *x, int *y)
    int          tok_str(Tokenizer *tok, const char *str,
                         int *n, const char ***items)



#cdef extern from "filecomplete.h":
    
    #
    #  This is actually in filecomplete.h
    #
    int fn_complete(EditLine *el,
                char *(*complet_func)(const char *, int),
                char **(*attempted_completion_function)(const char *, int, int),
                const char *word_break, const char *special_prefixes,
                const char *(*app_func)(const char *), size_t query_items,
                int *completion_type, int *over, int *point, int *end)
