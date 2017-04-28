#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.69])
AC_INIT([FULL-PACKAGE-NAME], [VERSION], [BUG-REPORT-ADDRESS])
#AC_CONFIG_SRCDIR([src/hello.c])
AC_CONFIG_HEADERS([config.h])

# support macros
AC_CONFIG_MACRO_DIR([m4])

# Checks for programs.
AC_PROG_CC

# Checks for libraries.

# Checks for header files.
AC_CHECK_HEADERS([stdlib.h])

# Checks for typedefs, structures, and compiler characteristics.

# Checks for library functions.

LIB_no_line_editor=$LIBS

# check where readline lives
# save the value of LIBS so we don't actually link Python with readline
LIBS_no_readline=$LIBS

# On some systems we need to link readline to a termcap compatible
# library.  NOTE: Keep the precedence of listed libraries synchronised
# with setup.py.
py_cv_lib_readline=no
AC_MSG_CHECKING([how to link readline libs])
for py_libtermcap in "" tinfo ncursesw ncurses curses termcap; do
  if test -z "$py_libtermcap"; then
    READLINE_LIBS="-lreadline"
  else
    READLINE_LIBS="-lreadline -l$py_libtermcap"
  fi
  LIBS="$READLINE_LIBS $LIBS_no_readline"
  AC_LINK_IFELSE(
    [AC_LANG_CALL([],[readline])],
    [py_cv_lib_readline=yes])
  if test $py_cv_lib_readline = yes; then
    break
  fi
done
# Uncomment this line if you want to use READINE_LIBS in Makefile or scripts
#AC_SUBST([READLINE_LIBS])
if test $py_cv_lib_readline = no; then
  AC_MSG_RESULT([none])
else
  AC_MSG_RESULT([$READLINE_LIBS])
fi

# check for readline file linked to libedit
AC_CHECK_LIB(readline, el_init,
	[py_cv_lib_readline_actually_libedit=yes],
	[py_cv_lib_readline_actually_libedit=no],
        $READLINE_LIBS)

LIBS=$LIBS_no_readline

LIBS_no_libedit=$LIBS

py_cv_lib_edit=no
# Check for the true libedit here as well
AC_MSG_CHECKING([how to link libedit libs])
for py_libtermcap in "" tinfo ncursesw ncurses curses termcap; do
  if test -z "$py_libtermcap"; then
    EDITLINE_LIBS="-ledit"
  else
    EDITLINE_LIBS="-ledit -l$py_libtermcap"
  fi
  LIBS="$EDITLINE_LIBS $LIBS_no_readline"
  AC_LINK_IFELSE(
    [AC_LANG_CALL([],[el_init])],
    [py_cv_lib_edit=yes])
  if test $py_cv_lib_edit = yes; then
    break
  fi
done
# Uncomment this line if you want to use EDITLINE_LIBS in Makefile or scripts
#AC_SUBST([EDITLINE_LIBS])
if test $py_cv_lib_edit = no; then
  AC_MSG_RESULT([none])
else
  AC_MSG_RESULT([$EDITLINE_LIBS])
  #AC_DEFINE(HAVE_LIBEDIT, 1,
  #  [Define if you have the libedit library (-ledit) supporting readline])
fi

# restore
LIBS=$LIBS_no_libedit

# select our choice for line-editor
if test $py_cv_lib_edit = yes || \
   test $py_cv_lib_readline_actually_libedit = yes ; then

   line_editor_lib=edit
   line_editor_result=libedit
   py_cv_line_editor_header=editline/readline.h
   LINE_EDITOR_LIBS=$EDITLINE_LIBS

   AC_CHECK_LIB(edit, readline,
	[py_cv_line_editor_supports_readline=yes],
	[py_cv_line_editor_supports_readline=no],
     	$LINE_EDITOR_LIBS)

   AC_CHECK_LIB(edit, history_init,
	[py_cv_edit_supports_history=yes],
	[py_cv_edit_supports_history=no],
	$LINE_EDITOR_LIBS)

   AC_DEFINE(HAVE_LIBEDIT, 1,
        [Define if you have the edit library (-ledit).])
    
    if test $py_cv_line_editor_supports_readline = yes; then
        AC_DEFINE(HAVE_LIBEDIT_READLINE, 1,
	   [Define if you have true libedit with readline support])
    fi

elif test $py_cv_lib_readline = yes; then

   line_editor_lib=readline
   line_editor_result=libreadline
   py_cv_line_editor_supports_readline=yes
   py_cv_line_editor_header=readline/readline.h
   LINE_EDITOR_LIBS=$READLINE_LIBS

    AC_DEFINE(HAVE_LIBREADLINE, 1,
 	[Define if you have the readline library (-lreadline).])

else

    # no support
    line_editor_lib=none
    line_editor_result=none
    py_cv_line_editor_supports_readline=no
    py_cv_line_editor_header=

fi

AC_MSG_CHECKING(selecting line-editor)
AC_MSG_RESULT($line_editor_result)

AC_SUBST(LINE_EDITOR, $line_editor_result)
AC_SUBST(LINE_EDITOR_LIBS)
AC_DEFINE_UNQUOTED([LINE_EDITOR], ["$line_editor_result"], [Preferred line-editor library])
AC_DEFINE_UNQUOTED([LINE_EDITOR_LIBS], ["$LINE_EDITOR_LIBS"], [Required libraries to link])


if test $py_cv_line_editor_supports_readline = yes; then

# check for readline 2.1
AC_CHECK_LIB($line_editor_lib, rl_callback_handler_install,
	[py_cv_readline_have_rl_callback=yes],
	[py_cv_readline_have_rl_callback=no],
	$LINE_EDITOR_LIBS)

# check for readline 2.2
AC_PREPROC_IFELSE(
  [AC_LANG_SOURCE([[#include < $py_cv_line_editor_header >]])],
  [have_readline_h=yes],
  [have_readline_h=no]
)
if test $have_readline_h = yes
then
  AC_EGREP_HEADER([extern int rl_completion_append_character;],
  [$py_cv_line_editor_header],
  AC_DEFINE(HAVE_RL_COMPLETION_APPEND_CHARACTER, 1,
  [Define if you have readline 2.2]), )
  AC_EGREP_HEADER([extern int rl_completion_suppress_append;],
  [$py_cv_line_editor_header],
  AC_DEFINE(HAVE_RL_COMPLETION_SUPPRESS_APPEND, 1,
  [Define if you have rl_completion_suppress_append]), )
fi

# check for readline 4.0
AC_CHECK_LIB($line_editor_lib, rl_pre_input_hook,
	[py_cv_readline_have_rl_pre_input_hook=yes],
	[py_cv_readline_have_rl_pre_input_hook=no],
	$LINE_EDITOR_LIBS)

# also in 4.0
AC_CHECK_LIB($line_editor_lib, rl_completion_display_matches_hook,
	[py_cv_readline_have_rl_completion_display_matches_hook=yes],
	[py_cv_readline_have_rl_completion_display_matches_hook=no],
	$LINE_EDITOR_LIBS)

# also in 4.0, but not in editline
AC_CHECK_LIB($line_editor_lib, rl_resize_terminal,
	[py_cv_readline_have_rl_resize_terminal=yes],
	[py_cv_readline_have_rl_resize_terminal=no],
	$LINE_EDITOR_LIBS)

# check for readline 4.2
AC_CHECK_LIB($line_editor_lib, rl_completion_matches,
	[py_cv_readline_have_rl_completion_matches=yes],
	[py_cv_readline_have_rl_completion_matches=no],
	$LINE_EDITOR_LIBS)

# also in readline 4.2
if test $have_readline_h = yes
then
  AC_EGREP_HEADER([extern int rl_catch_signals;],
  [$py_cv_line_editor_header],
  AC_DEFINE(HAVE_RL_CATCH_SIGNAL, 1,
  [Define if you can turn off readline's signal handling.]), )
fi

AC_CHECK_LIB($line_editor_lib, append_history,
	[py_cv_readline_have_rl_append_history=yes],
	[py_cv_readline_have_rl_append_history=no],
	$LINE_EDITOR_LIBS)

# End of readline checks: restore LIBS
LIBS=$LIBS_no_line_editor


  if test $py_cv_readline_have_rl_callback = yes; then
      AC_DEFINE(HAVE_RL_CALLBACK, 1, [Define if you have readline 2.1])
  fi

  if test $py_cv_readline_have_rl_pre_input_hook = yes; then
      AC_DEFINE(HAVE_RL_PRE_INPUT_HOOK, 1, [Define if you have readline 4.0])
  fi

  if test $py_cv_readline_have_rl_completion_display_matches_hook = yes; then
      AC_DEFINE(HAVE_RL_COMPLETION_DISPLAY_MATCHES_HOOK, 1,
      [Define if you have readline 4.0])
  fi
    
  if test $py_cv_readline_have_rl_resize_terminal = yes; then 
      AC_DEFINE(HAVE_RL_RESIZE_TERMINAL, 1, [Define if you have readline 4.0])
  fi

  if test $py_cv_readline_have_rl_completion_matches = yes; then
      AC_DEFINE(HAVE_RL_COMPLETION_MATCHES, 1,
	    [Define if you have readline 4.2])
  fi
    
  if test $py_cv_readline_have_rl_append_history = yes; then
      AC_DEFINE(HAVE_RL_APPEND_HISTORY, 1,
	   [Define if readline supports append_history])
  fi

fi

AC_OUTPUT
