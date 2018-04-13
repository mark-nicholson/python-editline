"""
Verifying the completer will properly complete various forms of lists.
"""

import sys
import re
import unittest
from test.support import import_module

# just grab what we need from the other...
from editline.tests.test_lineeditor import CompletionsBase

#
#  Check List support
#

class Completions_List(CompletionsBase):
    prep_script = [
        'a = [ 1,2,3,4,5 ]'
        ]
    cmd = 'a[2]'
    cmd_tab_index = 2
    result = '3'
    comp = ''
    comp_regexp = re.compile(r'0\s+1\s+2\s+3\s+4')

class Completions_ListEmpty(CompletionsBase):
    prep_script = [
        'a = []'
        ]
    tidy_cmd = '\b\b'
    tidy_len = 0

class Completions_List_Long(Completions_List):
    prep_script = [
        'a = [ 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20 ]'
        ]
    cmd = 'a[12]'
    cmd_tab_index = 3
    result = '13'
    comp_regexp = re.compile(r'1\s+10\s+11\s+12\s+13\s+14\s+15\s+16\s+17\s+18\s+19')

class Completions_Range(Completions_List_Long):
    prep_script = [
        'a = range(1,21)'
        ]

class Completions_Set(Completions_List_Long):
    """Sets will tab-complete as an array, but the lookup cannot be done"""
    prep_script = [
        'a = set(range(1,21))'
        ]
    tidy_cmd = 'clear()'    # array index is invalid, so replace the op
    tidy_len = 0
    result = ''             # prints nothing
    comp = None

class Completions_FrozenSet(Completions_Set):
    prep_script = [
        'a = frozenset(range(1,21))'
        ]
    tidy_cmd = '\b\b\b'
    tidy_len = 0
    result = 'frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20})'
    timeout = 5

class Completions_List_FnArg(Completions_List):
    """tab should present all list index options"""
    cmd = "print(a[2])"
    cmd_tab_index = 8
    tidy_cmd = '2])'
    tidy_len = 1

class Completions_List_FnArg_with_Space(Completions_List_FnArg):
    """tab should present all list index options, regardless of space"""
    cmd = "print( a[2])"
    cmd_tab_index = 9

class Completions_List_FnArg_Multi(Completions_List):
    """tab should complete list item"""
    cmd = "print(a[2])"
    cmd_tab_index = 9
    tidy_cmd = ')'
    tidy_len = 1
    comp_len = 0
    comp_idx = None

class Completions_List_FnArg_Multi_with_Space(Completions_List_FnArg_Multi):
    """tab should complete list item, regardless of preceding space"""
    cmd = "print( a[2])"
    cmd_tab_index = 10

class Completions_List_Assign(Completions_List):
    """tab should auto-add the text to complete the list text"""
    cmd = 'x=a[2]'
    cmd_tab_index = 5
    tidy_cmd = ''
    tidy_len = 0
    comp_len = 0
    comp_idx = None

class Completions_List_Assign_with_Space(Completions_List_Assign):
    """tab should auto-add the text to complete the list text,
    regardless of spaces.
    """
    cmd = 'x = a[2]'
    cmd_tab_index = 7

class Completions_List_AssignMulti(Completions_List):
    """tab should present all list indicies as completion options"""
    cmd = 'x=a[2]'
    cmd_tab_index = 4
    tidy_cmd = '2]'
    tidy_len = 0
    comp_len = 2
    comp_idx = 0

class Completions_List_AssignMulti_with_Space(Completions_List_AssignMulti):
    """tab should present all list indicies as completion options
    regardless of spaces.
    """
    cmd = 'x = a[2]'
    cmd_tab_index = 6


if __name__ == "__main__":
    unittest.main()
