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
# Check the cache for headers and library name
#
AC_CACHE_CHECK([preferred line-editor library],
		[ac_cv_line_editor],
		[ac_cv_line_editor=edit])
AC_CACHE_CHECK([preferred line-editor header],
		[ac_cv_line_editor_header],
		[ac_cv_line_editor_header=histedit.h])

# init common vars
AX_INIT_LIBEDIT_API()

#
#  Check the values, either cached or pre-set
#
AS_VAR_IF(ac_cv_line_editor, [none],
	[ac_cv_line_editor_header=],
	[AX_CHECK_LIB_LINK($ac_cv_line_editor,
			[el_init],
			[$ac_line_editor_term_libs],
			[AX_CHECK_LIBEDIT_API($ac_cv_line_editor,
						[$ac_cv_line_editor_header],
						[],
						[ac_cv_line_editor=none])],
			[ac_cv_line_editor=none])
		])

#
#  Done
#
AC_OUTPUT
