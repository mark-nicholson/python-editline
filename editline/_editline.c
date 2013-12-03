/*
 * _editline.c -- raw extension of libedit
 *
 */

#include "Python.h"
#include "structmember.h"
#include "histedit.h"

typedef struct
{
    PyObject_HEAD
    EditLine *el;
    /*
    #ifdef WITH_THREAD
        PyThread_type_lock lock;
    #endif
    */
} PyEditLine;
