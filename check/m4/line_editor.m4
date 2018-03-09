
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
