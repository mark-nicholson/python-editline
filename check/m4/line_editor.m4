
## --------------------------------- ##
## 1. Generic tests for libraries.## ##
## --------------------------------- ##

#
# AC_CHECK_LIB_LINK(LIBRARY, FUNCTION, LINK-LIBS)
#                   [ACTION-IF-LINKED], [ACTION-IF-NOT-LINKED])
# --------------------------------------------------------
# Try linking against LIBRARY and see which of the LINK-LIBS is needed
#  defines:  ac_cv_link_lib_$1 to the list of libs needed
#
AC_DEFUN([AC_CHECK_LIB_LINK], [
  AS_VAR_PUSHDEF([ac_Link], [ac_cv_link_lib_$1])
  # track if this ever linked
  ac_func_link_succeeded=no
  # make sure we don't accidentally remember this
  ac_func_link_save_LIBS=$LIBS
  # general message
  AC_MSG_CHECKING([how to link lib$1])
  # iterate over the list of libs provided
  for ac_func_link_testlib in "" $3; do
    if test -z "$ac_func_link_testlib"; then
      ac_func_link_libs="-l$1"
    else
      ac_func_link_libs="-l$1 -l$ac_func_link_testlib"
    fi
    #AC_MSG_CHECKING([$1 links: $ac_func_link_libs])
    LIBS="$ac_func_link_libs $ac_func_link_save_LIBS"
    # this is basically AC_SEARCH_LIBS with no cache/side-effects
    altc_lib_line_editor=check
    AC_LINK_IFELSE(
      [AC_LANG_CALL([],[$2])],
      [#AC_MSG_RESULT([yes])
      ac_func_link_succeeded=yes
      AS_VAR_SET([ac_Link], [$ac_func_link_testlib])
      break],
      [#AC_MSG_RESULT([no])
      continue
      ])
  done
  # restore the original, unmolested LIBS
  LIBS=$ac_func_link_save_LIBS
  # extra checking
  if test $ac_func_link_succeeded != yes; then
    # library does not exist
    AC_MSG_RESULT([unavailable])
    # caller stuff
    $4
  else
    # report the library needs
    AS_VAR_COPY([ac_link_info], [ac_Link])
    AS_VAR_IF([ac_Link], [],
      [AC_MSG_RESULT([no extra libs])], 
      [AC_MSG_RESULT([$ac_Link])])
    # caller stuff
    $5
  fi
  AS_VAR_POPDEF([ac_Link])
])

################################################################################
#
#  LibEdit API Inspection Support
#
################################################################################

#
# Routine to define the lists of symbols for libedit
#
AC_DEFUN([AC_INIT_LIBEDIT_API], [
  AS_VAR_SET([ac_line_editor_libedit_fcns],
	     ["el_init el_get el_set el_line el_insertstr el_gets \
	       el_source el_reset el_end tok_init tok_end history \
	       history_init history_end"])
  AS_VAR_SET([ac_line_editor_libedit_tokens],
	     ["EL_EDITOR EL_SIGNAL EL_PROMPT_ESC EL_RPROMPT_ESC EL_HIST \
	       EL_ADDFN EL_BIND EL_CLIENTDATA EL_REFRESH EL_GETTC H_ENTER"])
])	     


#
# AC_CHECK_LIBEDIT_API(LIBRARY, HEADER-FILE)
# --------------------------------------------------------
#   Discern if the given library has a decent libedit api
#    defines:
#       ac_cv_have_decl_TOKEN_NAME=yes   (if found)
#       ac_cv_lib_edit___fnname=yes      (if found)
#
AC_DEFUN([AC_CHECK_LIBEDIT_API], [
  # rename the arguments to something clearer
  ac_elapi_lib=$1
  ac_elapi_headers="$2"
  AS_VAR_COPY([ac_elapi_link_libs], [ac_cv_link_lib_$1])
  # tracking vars
  ac_elapi_var=ac_cv_lib_$1___
  AS_VAR_PUSHDEF([ac_elapi_ver], [ac_cv_lib_$1_elapi_version])
  # basic init
  AC_INIT_LIBEDIT_API()
  AS_VAR_SET([ac_elapi_ver], [0.0])
  # make sure we have them.
  for ac_fcn in $ac_line_editor_libedit_fcns; do
    ac_elapi_LIBS=$LIBS
    AC_CHECK_LIB($ac_elapi_lib, $ac_fcn, [], [], [$ac_elapi_link_libs])
    LIBS=$ac_elapi_LIBS
  done
  # header tokens needed
  for ac_tok in $ac_line_editor_libedit_tokens; do
    AC_CHECK_DECLS([$ac_tok], [], [], [[#include <$2>]])
  done
])



#
# AC_CHECK_READLINE_API(LIBRARY, HEADER-FILE)
# --------------------------------------------------------
#   Discern if the given library has a decent readline api
#    defines:  ac_cv_link_lib_$1 to the list of libs needed
#
AC_DEFUN([AC_CHECK_READLINE_API], [
  # rename the arguments to something clearer
  ac_rlapi_lib=$1
  AS_VAR_COPY([ac_rlapi_link_libs], [ac_cv_link_lib_$1])
  # tracking vars
  AS_VAR_PUSHDEF([ac_rlapi_ver], [ac_cv_$1_rlapi_version])
  AS_VAR_PUSHDEF([ac_rlapi_have_rl_callback], [ac_cv_$1_rlapi_have_rl_callback])
  # basic init
  AS_VAR_SET([ac_rlapi_ver], [0.0])

  # check for readline 2.1
  AC_CHECK_LIB($ac_rlapi_lib, rl_callback_handler_install,
	[AS_VAR_SET([ac_rlapi_ver], [2.1])], [],
	[$ac_rlapi_link_libs])

  # check for readline 2.2
  AC_PREPROC_IFELSE(
    [AC_LANG_SOURCE([[#include < $2 >]])],
    [have_readline_h=yes],
    [have_readline_h=no])
  

# if test $have_readline_h = yes
# then
#   AC_EGREP_HEADER([extern int rl_completion_append_character;],
#   [$py_cv_line_editor_header],
#   AC_DEFINE(HAVE_RL_COMPLETION_APPEND_CHARACTER, 1,
#   [Define if you have readline 2.2]), )
#   AC_EGREP_HEADER([extern int rl_completion_suppress_append;],
#   [$py_cv_line_editor_header],
#   AC_DEFINE(HAVE_RL_COMPLETION_SUPPRESS_APPEND, 1,
#   [Define if you have rl_completion_suppress_append]), )
# fi

  # check for readline 4.0
  AC_CHECK_LIB($ac_rlapi_lib, rl_pre_input_hook,
	[AS_VAR_SET([ac_rlapi_ver], [4.0])], [], [$ac_rlapi_link_libs])

  # also in 4.0
  AC_CHECK_LIB($ac_rlapi_lib, rl_completion_display_matches_hook,
	[AS_VAR_SET([ac_rlapi_ver], [4.0])], [], [$ac_rlapi_link_libs])

  # also in 4.0, but not in editline
  AC_CHECK_LIB($ac_rlapi_lib, rl_resize_terminal,
	[AS_VAR_SET([ac_rlapi_ver], [4.0])], [], [$ac_rlapi_link_libs])

  # check for readline 4.2
  AC_CHECK_LIB($ac_rlapi_lib, rl_completion_matches,
  	[AS_VAR_SET([ac_rlapi_ver], [4.2])], [], [$ac_rlapi_link_libs])

  # check for readline 4.2
  AC_CHECK_LIB($ac_rlapi_lib, rl_completion_matches,
  	[AS_VAR_SET([ac_rlapi_ver], [4.2])], [], [$ac_rlapi_link_libs])

# # also in readline 4.2
# if test $have_readline_h = yes
# then
#   AC_EGREP_HEADER([extern int rl_catch_signals;],
#   [$py_cv_line_editor_header],
#   AC_DEFINE(HAVE_RL_CATCH_SIGNAL, 1,
#   [Define if you can turn off readline's signal handling.]), )
# fi

  AC_CHECK_LIB($ac_rlapi_lib, append_history,
  	[AS_VAR_SET([ac_rlapi_ver], [4.2])], [], [$ac_rlapi_link_libs])
])

