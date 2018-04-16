"""
Verifying the completer will properly complete various forms of dictionaries.
"""

import sys
import re
import unittest
from test.support import import_module

# just grab what we need from the other...
from editline.tests.test_lineeditor import CompletionsBase, CompletionsCommon

#
#  Check Dictionary support
#

class Completions_Dictionary(CompletionsCommon):
    prep_script = [
        'a = { "tomatoes": 10, "peaches": 5, "pears": 8, "pecans": 100 }'
        ]
    cmd = "a['tomatoes']"
    cmd_tab_index = 7
    result = '10'
    tidy_cmd = ''
    tidy_len = 1
    comp = None
    comp_len = 0

class Completions_Dictionary_NotArray(Completions_Dictionary):
    cmd = "a['pecans']"
    cmd_tab_index = 2
    tidy_cmd = "pecans']"
    result = '100'
    comp_len = 2
    comp = re.compile(r'peaches\s+pears\s+pecans\s+tomatoes')

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
    comp = re.compile(r'peaches\s+pears\s+pecans')

class Completions_Dictionary_Multi2(Completions_Dictionary_Multi):
    cmd = "a['pears']"
    cmd_tab_index = 6
    result = '8'
    comp = re.compile(r'peaches\s+pears')

#
#  Multi-Level Dictionaries
#

class Completions_Dict3D_L1(CompletionsBase):
    prep_script = [
        'from editline.tests.support.data_structures import three_d_dict'
    ]
    cmd = "three_d_dict['zero']['zero_one']['zero_one_two']"
    cmd_tab_index = 14
    result = '{:d}'.format(0x012)
    comp = re.compile(r'one\s+three\s+two\s+zero')
    comp_idx = 0
    comp_len = 2

class Completions_Dict3D_L2(Completions_Dict3D_L1):
    cmd_tab_index = 22
    tidy_cmd = "one']['zero_one_two']"
    comp = re.compile(r'zero_one\s+zero_two\s+zero_zero')

class Completions_Dict3D_L3(Completions_Dict3D_L1):
    cmd_tab_index = 34
    tidy_cmd = "two']"
    comp = re.compile(r'zero_one_one\s+zero_one_three\s+zero_one_two\s+zero_one_zero')

class Completions_Dict3D_L1_MultiKey(Completions_Dict3D_L1):
    cmd = "three_d_dict['three']['three_two']['three_two_two']"
    cmd_tab_index = 15
    result = '{:d}'.format(0x322)
    comp = re.compile(r'three\s+two')
    
# L2 has no conflicting keys

class Completions_Dict3D_L3_MultiKey(Completions_Dict3D_L1_MultiKey):
    cmd_tab_index = 47
    tidy_cmd = "wo']"
    comp = re.compile(r'three_two_three\s+three_two_two')

    
# kick off 
if __name__ == "__main__":
    unittest.main()
