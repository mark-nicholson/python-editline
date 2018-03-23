#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.69])

AC_INIT([Python-EditLine], [1.0], [bugs@tbd.com])

AC_CONFIG_HEADERS([config.h])

# support macros
AC_CONFIG_MACRO_DIR([m4])

# Checks for programs.
AC_PROG_CC


#
#  GNU Readline
#
AC_CHECK_HEADER([readline/readline.h],
		[py_ac_have_gnu_readline_h=readline/readline.h])

#AC_DEFINE([HAVE_GNU_READLINE_H], [1], [GNU Readline headers])

AC_CHECK_LIB_LINK([readline], [readline],
	      	  [tinfo ncursesw ncurses curses termcap])

# libreadline usable?
AS_VAR_SET_IF([ac_cv_link_lib_readline],
	      [AS_VAR_SET_IF([py_ac_have_gnu_readline_h],
	        [ac_leditor_readline_usable=yes],
	        [ac_leditor_readline_usable=no])],
	      [ac_leditor_readline_usable=no])

# see if libreadline is actually 'libedit' here...
AC_CHECK_LIBEDIT_API([readline], [readline/readline.h])



#
# Troglobit libeditline
#
AC_CHECK_HEADER([editline.h],
		[py_ac_have_editline_h=editline.h])

AC_CHECK_LIB_LINK([editline], [readline],
	      	  [tinfo ncursesw ncurses curses termcap])

# libeditline usable?
AS_VAR_SET_IF([ac_cv_link_lib_editline],
	      [AS_VAR_SET_IF([py_ac_have_editline_h],
	        [ac_leditor_editline_usable=yes],
	        [ac_leditor_editline_usable=no])],
	      [ac_leditor_editline_usable=no])


#
# *BSD libedit
#
AC_CHECK_HEADER([histedit.h],
		 [py_ac_have_bsd_libedit_h=histedit.h],
		 [AC_CHECK_HEADER([histedit.h editline/readline.h],
		   [py_ac_have_bsd_libedit_h=editline/readline.h])])

AC_CHECK_LIB_LINK([edit], [readline],
	      	  [tinfo ncursesw ncurses curses termcap])


# libedit usable?
AS_VAR_SET_IF([ac_cv_link_lib_edit],
	      [AS_VAR_SET_IF([py_ac_have_bsd_libedit_h], 
	        [ac_leditor_libedit_usable=yes],
	        [ac_leditor_libedit_usable=no])],
	      [ac_leditor_libedit_usable=no])


#
#  Summarize which even appear to be usable
#
AC_MSG_CHECKING([libreadline usable])
AC_CHECK_LIBEDIT_API([$ac_cv_line_editor_library],
		     [$ac_cv_line_editor_header])
AC_MSG_RESULT([$ac_leditor_readline_usable])

AC_MSG_CHECKING([libeditline usable])
AC_MSG_RESULT([$ac_leditor_editline_usable])

AC_MSG_CHECKING([libedit usable])
AC_MSG_RESULT([$ac_leditor_libedit_usable])


#
#  User would need to specify which combination they want:
#     c-library
#     python extension
#
#  The default would be:
#     GNU libreadline
#     readline.so
#
# Options:
#   library:   gnureadline, editline, libedit, none  (none means 'builtin')
#   extension: readline.so, editline.so
#
AC_CACHE_CHECK([preferred line-editor library],
               [ac_cv_line_editor],
	       [ac_cv_line_editor=gnureadline])
AC_CACHE_CHECK([preferred line-editor extension],
               [ac_cv_line_editor_extension],
	       [ac_cv_line_editor_extension=readline.so])




#
# Validate the combination
#
AC_MSG_NOTICE([DBG: $ac_cv_line_editor])
AC_MSG_NOTICE([DBG: $ac_cv_line_editor_extension])

case $ac_cv_line_editor in
  libedit)
	if test $ac_leditor_libedit_usable != yes ; then
	   ac_cv_line_editor_library=none
	   AC_MSG_NOTICE([LibEdit requested as line-editor, but not available. Using built-in.])
	else
	    ac_cv_line_editor_library=edit
	fi
	case $ac_cv_line_editor_extension in
	  editline.so|readline.so)
		break
		;;
	  *)
		# set the default
		AC_MSG_NOTICE([Defaulting editline.so usage with libedit])
		ac_cv_line_editor_extension=editline.so
		break
		;;
	esac
	break
	;;

  editline)
	if test $ac_leditor_editline_usable != yes ; then
	   AC_MSG_FAILURE([EditLine requested as line-editor, but not available])
	fi
	ac_cv_line_editor_library=editline
	case $ac_cv_line_editor_extension in
	  editline.so|readline.so)
		break
		;;
	  *)
		# set the default
		AC_MSG_NOTICE([Defaulting readline.so usage with libeditline])
		ac_cv_line_editor_extension=readline.so
		break
		;;
	esac
	break
	;;

  gnureadline)
	if test $ac_leditor_readline_usable != yes ; then
	   AC_MSG_FAILURE([ReadLine requested as line-editor, but not available])
	fi
	ac_cv_line_editor_library=readline
	if test $ac_cv_line_editor_extension != "readline.so" ; then
	  # force it.  only one that works.
	  AC_MSG_NOTICE([Defaulting readline.so usage with libreadline])
	  ac_cv_line_editor_extension=readline.so
	fi
	break
	;;

  none)
	# only can work with editline.so
	ac_cv_line_editor_library=
	ac_cv_line_editor_extension=editline.so
	ac_cv_line_editor_header=
	break
	;;

  *)
	AC_MSG_NOTICE([Defaulting readline.so usage with libreadline])
	ac_cv_line_editor=gnureadline
	ac_cv_line_editor_library=readline
	ac_cv_line_editor_extension=readline.so
	break
	;;
esac

#
#  Check for the required APIs for the extensions
#
case $ac_cv_line_editor_extension in
    editline.so)
        if test $ac_cv_line_editor_library != none ; then
            AC_CHECK_LIBEDIT_API([$ac_cv_line_editor_library],
				 [$ac_cv_line_editor_header])
	else
	    AC_MSG_NOTICE([Skipping checks for builtin libedit])
	fi
	break
	;;

    *)
        AC_CHECK_READLINE_API([$ac_cv_line_editor_library],
			      [$ac_cv_line_editor_header])
	break
	;;
esac

#
#  Review the support available, then figure out if we need to
#  downshift to use the "builtin" version of libedit.
#





dnl if test $ac_cv_line_editor_library = readline && \
dnl    test $ac_cv_line_editor_extension = readline ; then

dnl fi

dnl # select our choice for line-editor
dnl if test $py_cv_lib_edit = yes || \
dnl    test $py_cv_lib_readline_actually_libedit = yes ; then

dnl    line_editor_lib=edit
dnl    line_editor_result=libedit
dnl    py_cv_line_editor_header=editline/readline.h
dnl    LINE_EDITOR_LIBS=$EDITLINE_LIBS

dnl    AC_CHECK_LIB(edit, readline,
dnl 	[py_cv_line_editor_supports_readline=yes],
dnl 	[py_cv_line_editor_supports_readline=no],
dnl      	$LINE_EDITOR_LIBS)

dnl    AC_CHECK_LIB(edit, history_init,
dnl 	[py_cv_edit_supports_history=yes],
dnl 	[py_cv_edit_supports_history=no],
dnl 	$LINE_EDITOR_LIBS)

dnl    AC_DEFINE(HAVE_LIBEDIT, 1,
dnl         [Define if you have the edit library (-ledit).])
    
dnl     if test $py_cv_line_editor_supports_readline = yes; then
dnl         AC_DEFINE(HAVE_LIBEDIT_READLINE, 1,
dnl 	   [Define if you have true libedit with readline support])
dnl     fi

dnl elif test $py_cv_lib_readline = yes; then

dnl    line_editor_lib=readline
dnl    line_editor_result=libreadline
dnl    py_cv_line_editor_supports_readline=yes
dnl    py_cv_line_editor_header=readline/readline.h
dnl    LINE_EDITOR_LIBS=$READLINE_LIBS

dnl     AC_DEFINE(HAVE_LIBREADLINE, 1,
dnl  	[Define if you have the readline library (-lreadline).])

dnl else

dnl     # no support
dnl     line_editor_lib=none
dnl     line_editor_result=none
dnl     py_cv_line_editor_supports_readline=no
dnl     py_cv_line_editor_header=

dnl fi

AC_MSG_CHECKING(Selected line-editor library)
AC_MSG_RESULT($ac_cv_line_editor_library)
AC_MSG_CHECKING(Selected line-editor extension)
AC_MSG_RESULT($ac_cv_line_editor_extension)

AC_SUBST(LINE_EDITOR, $ac_cv_line_editor_library)
AC_SUBST(LINE_EDITOR_LIBS)
AC_DEFINE_UNQUOTED([LINE_EDITOR], ["$ac_cv_line_editor_library"], [Preferred line-editor library])
AS_VAR_COPY([py_ac_lelibs], [ac_cv_link_lib_$ac_cv_line_editor_library])
AC_DEFINE_UNQUOTED([LINE_EDITOR_LIBS], ["$py_ac_lelibs"], [Required libraries to link])


dnl if test $py_cv_line_editor_supports_readline = yes; then

dnl # check for readline 2.1
dnl AC_CHECK_LIB($line_editor_lib, rl_callback_handler_install,
dnl 	[py_cv_readline_have_rl_callback=yes],
dnl 	[py_cv_readline_have_rl_callback=no],
dnl 	$LINE_EDITOR_LIBS)

dnl # check for readline 2.2
dnl AC_PREPROC_IFELSE(
dnl   [AC_LANG_SOURCE([[#include < $py_cv_line_editor_header >]])],
dnl   [have_readline_h=yes],
dnl   [have_readline_h=no]
dnl )
dnl if test $have_readline_h = yes
dnl then
dnl   AC_EGREP_HEADER([extern int rl_completion_append_character;],
dnl   [$py_cv_line_editor_header],
dnl   AC_DEFINE(HAVE_RL_COMPLETION_APPEND_CHARACTER, 1,
dnl   [Define if you have readline 2.2]), )
dnl   AC_EGREP_HEADER([extern int rl_completion_suppress_append;],
dnl   [$py_cv_line_editor_header],
dnl   AC_DEFINE(HAVE_RL_COMPLETION_SUPPRESS_APPEND, 1,
dnl   [Define if you have rl_completion_suppress_append]), )
dnl fi

dnl # check for readline 4.0
dnl AC_CHECK_LIB($line_editor_lib, rl_pre_input_hook,
dnl 	[py_cv_readline_have_rl_pre_input_hook=yes],
dnl 	[py_cv_readline_have_rl_pre_input_hook=no],
dnl 	$LINE_EDITOR_LIBS)

dnl # also in 4.0
dnl AC_CHECK_LIB($line_editor_lib, rl_completion_display_matches_hook,
dnl 	[py_cv_readline_have_rl_completion_display_matches_hook=yes],
dnl 	[py_cv_readline_have_rl_completion_display_matches_hook=no],
dnl 	$LINE_EDITOR_LIBS)

dnl # also in 4.0, but not in editline
dnl AC_CHECK_LIB($line_editor_lib, rl_resize_terminal,
dnl 	[py_cv_readline_have_rl_resize_terminal=yes],
dnl 	[py_cv_readline_have_rl_resize_terminal=no],
dnl 	$LINE_EDITOR_LIBS)

dnl # check for readline 4.2
dnl AC_CHECK_LIB($line_editor_lib, rl_completion_matches,
dnl 	[py_cv_readline_have_rl_completion_matches=yes],
dnl 	[py_cv_readline_have_rl_completion_matches=no],
dnl 	$LINE_EDITOR_LIBS)

dnl # also in readline 4.2
dnl if test $have_readline_h = yes
dnl then
dnl   AC_EGREP_HEADER([extern int rl_catch_signals;],
dnl   [$py_cv_line_editor_header],
dnl   AC_DEFINE(HAVE_RL_CATCH_SIGNAL, 1,
dnl   [Define if you can turn off readline's signal handling.]), )
dnl fi

dnl AC_CHECK_LIB($line_editor_lib, append_history,
dnl 	[py_cv_readline_have_rl_append_history=yes],
dnl 	[py_cv_readline_have_rl_append_history=no],
dnl 	$LINE_EDITOR_LIBS)

dnl # End of readline checks: restore LIBS
dnl LIBS=$LIBS_no_line_editor


dnl   if test $py_cv_readline_have_rl_callback = yes; then
dnl       AC_DEFINE(HAVE_RL_CALLBACK, 1, [Define if you have readline 2.1])
dnl   fi

dnl   if test $py_cv_readline_have_rl_pre_input_hook = yes; then
dnl       AC_DEFINE(HAVE_RL_PRE_INPUT_HOOK, 1, [Define if you have readline 4.0])
dnl   fi

dnl   if test $py_cv_readline_have_rl_completion_display_matches_hook = yes; then
dnl       AC_DEFINE(HAVE_RL_COMPLETION_DISPLAY_MATCHES_HOOK, 1,
dnl       [Define if you have readline 4.0])
dnl   fi
    
dnl   if test $py_cv_readline_have_rl_resize_terminal = yes; then 
dnl       AC_DEFINE(HAVE_RL_RESIZE_TERMINAL, 1, [Define if you have readline 4.0])
dnl   fi

dnl   if test $py_cv_readline_have_rl_completion_matches = yes; then
dnl       AC_DEFINE(HAVE_RL_COMPLETION_MATCHES, 1,
dnl 	    [Define if you have readline 4.2])
dnl   fi
    
dnl   if test $py_cv_readline_have_rl_append_history = yes; then
dnl       AC_DEFINE(HAVE_RL_APPEND_HISTORY, 1,
dnl 	   [Define if readline supports append_history])
dnl   fi

dnl fi

AC_OUTPUT
