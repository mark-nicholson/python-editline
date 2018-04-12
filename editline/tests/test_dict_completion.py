"""
Verifying the completer will properly complete various forms of dictionaries.
"""

import sys
import re
import unittest
from test.support import import_module

# just grab what we need from the other...
from editline.tests.test_lineeditor import CompletionsBase

#
#  Check Dictionary support
#

class Completions_Dictionary(CompletionsBase):
    prep_script = [
        'a = { "tomatoes": 10, "peaches": 5, "pears": 8, "pecans": 100 }'
        ]
    cmd = "a['tomatoes']"
    cmd_tab_index = 7
    result = '10'
    tidy_cmd = ''
    tidy_len = 1
    comp = ''
    comp_idx = None
    comp_len = 0
    comp_regexp = re.compile(r'0\s+1\s+2\s+3\s+4')

class Completions_Dictionary_MultiUnique(Completions_Dictionary):
    cmd = "a['pecans']"
    cmd_tab_index = 6
    result = '100'

class Completions_Dictionary_Multi(Completions_Dictionary):
    cmd = "a['pecans']"
    cmd_tab_index = 5
    result = '100'
    tidy_cmd = None
    tidy_len = None
    comp_idx = 0
    comp_len = 2
    comp_regexp = re.compile(r'peaches\s+pears\s+pecans')

class Completions_Dictionary_Multi2(Completions_Dictionary_Multi):
    cmd = "a['pears']"
    cmd_tab_index = 6
    result = '8'
    comp_regexp = re.compile(r'peaches\s+pears')

class Completions_Dict_FnArg(Completions_Dictionary):
    cmd = "print(a['tomatoes'])"
    cmd_tab_index = 12
    tidy_cmd = ')'   # gotta close the print statement
    tidy_len = 1

class Completions_Dict_FnArg_with_space(Completions_Dictionary):
    cmd = "print( a['tomatoes'])"
    cmd_tab_index = 12
    tidy_cmd = ')'   # gotta close the print statement
    tidy_len = 1

class Completions_Dict_Assign(Completions_Dictionary):
    cmd = "x = a['tomatoes']"
    cmd_tab_index = 12
    tidy_cmd = ''
    tidy_len = 0

class Completions_Dict_Multi_FnArg(Completions_Dictionary_Multi):
    cmd = "print(a['pecans'])"
    cmd_tab_index = 11

class Completions_Dict_Multi_FnArg_with_space(Completions_Dictionary_Multi):
    cmd = "print( a['pecans'])"
    cmd_tab_index = 12

class Completions_Dict_Multi_Assign(Completions_Dictionary_Multi):
    cmd = "x = a['pecans']"
    cmd_tab_index = 9
    tidy_cmd = None
    tidy_len = 0


# kick off 
if __name__ == "__main__":
    unittest.main()
