"""
Verifying the completer will properly complete various forms of lists.
"""

import sys
import re
import unittest
from test.support import import_module

# just grab what we need from the other...
from editline.tests.test_lineeditor import CompletionsBase, CompletionsCommon

#
#  Check List support
#

class Completions_List(CompletionsCommon):
    prep_script = [
        'a = [1,2,3,4,5]'
        ]
    cmd = 'a[2]'
    cmd_tab_index = 2
    result = '3'
    comp = re.compile(r'0\s+1\s+2\s+3\s+4')

class Completions_ListEmpty(CompletionsBase):
    prep_script = [
        'a = []'
        ]
    tidy_cmd = '\b\b'
    tidy_len = 0
    result = ''

class Completions_List_Long(Completions_List):
    prep_script = [
        'a = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]'
        ]
    cmd = 'a[12]'
    cmd_tab_index = 3
    result = '13'
    comp = re.compile(r'1\s+10\s+11\s+12\s+13\s+14\s+15\s+16\s+17\s+18\s+19')

class Completions_Range(Completions_List_Long):
    prep_script = [
        'a = range(1,21)'
        ]

class Completions_Set(Completions_List_Long):
    """Sets will tab-complete as an array, but the lookup cannot be done"""
    prep_script = [
        'a = set(range(1,21))'
        ]
    tidy_cmd = 'copy()'     # array index is invalid, so replace the op
    tidy_len = 1
    result = '{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20}'
    comp = re.compile(r'a.add\(\s+a.clear\(')
    comp_len = 10

class Completions_FrozenSet(Completions_Set):
    prep_script = [
        'a = frozenset(range(1,21))'
        ]
    tidy_cmd = 'copy()'
    tidy_len = 1
    result = 'frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20})'
    timeout = 5
    comp = re.compile(r'a.copy\(\s+a.difference\(')
    comp_len = 4


if __name__ == "__main__":
    unittest.main()
