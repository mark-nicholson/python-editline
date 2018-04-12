
import sys
import re
import unittest
from test.support import import_module

# just grab what we need from the other...
from test_lineeditor import CompleterBase, CompletionsBase

class Completer_LoadModule(CompleterBase):

    def test_001_load(self):
        output = self.tool.cmd('from editline.test.support import widechar')
        self.assertEqual(len(output), 0)

class Completions_ExtModule(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar'
    ]
    cmd = 'widechar.__name__'
    cmd_tab_index = 1
    result = 'editline.test.support.widechar'
    tidy_cmd = None
    tidy_len = None
    comp_len = 2
    comp_idx = 0
    comp_regexp = r'while\s+widechar.\s+with'
    timeout = 3

class Completions_ExtModule_NoAlts(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar'
    ]
    cmd = 'widechar.__name__'
    cmd_tab_index = 4
    result = 'editline.test.support.widechar'
    tidy_cmd = '__name__'
    tidy_len = None
    comp_len = 0
    comp_idx = None
    timeout = 3

class Completions_ExtModule_Class(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar'
    ]
    cmd = 'widechar.__name__'
    cmd_tab_index = 9
    result = 'editline.test.support.widechar'
    tidy_cmd = '__name__'
    tidy_len = None
    comp_len = 3
    comp_idx = 0
    comp_regexp = r'widechar.Greek\(\s+widechar.Korean\(\s+widechar.Russian\(\s+widechar.Tamil\('
    timeout = 3


################################################################################
#
#  Test using Greek UTF8 Characters
#
################################################################################

class Completions_UTF8_GreekAttr(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'greek = widechar.Greek()'
    ]
    cmd = 'greek.__module__'
    cmd_tab_index = 6
    result = 'editline.test.support.widechar'
    tidy_cmd = None
    tidy_len = None
    comp_len = 4
    comp_idx = 1
    comp_regexp = r'greek.μυρωδιά\s+greek.οδηγω\s+greek.παίζω\s+greek.παραλείπω'
    timeout = 3

class Completions_UTF8_GreekAttrPrefix(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'greek = widechar.Greek()'
    ]
    cmd = 'print(greek.παίζω)'
    cmd_tab_index = 14
    result = 'play'
    tidy_cmd = None
    tidy_len = 1
    comp_len = 2
    comp_idx = 0
    comp_regexp = r'greek.παίζω\s+greek.παραλείπω'
    timeout = 3

class Completions_UTF8_GreekDictKey(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'greek = widechar.Greek()'
    ]
    cmd = "print(greek.actions['τρέξιμο'])"
    cmd_tab_index = 22
    result = '1'
    tidy_cmd = ')'
    tidy_len = 1
    comp_len = 0
    comp_idx = None
    #comp = '1'
    timeout = 3

class Completions_UTF8_GreekDictKey2(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'greek = widechar.Greek()'
    ]
    cmd = "print(greek.actions['παραλείπω'])"
    cmd_tab_index = 22
    result = '1'
    tidy_cmd = "ραλείπω'])"
    tidy_len = 1
    comp_len = 2
    comp_idx = 0
    comp_regexp = r'παίζω\s+παραλείπω'
    timeout = 3


################################################################################
#
#  Test using Korean UTF8 Characters
#
################################################################################

class Completions_UTF8_KoreanAttr(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'korean = widechar.Korean()'
    ]
    cmd = 'korean.__module__'
    cmd_tab_index = 7
    result = 'editline.test.support.widechar'
    tidy_cmd = None
    tidy_len = None
    comp_len = 4
    comp_idx = 1
    comp_regexp = r'korean.도약\s+korean.따르다\s+korean.롤\s+korean.리드'
    timeout = 3

class Completions_UTF8_KoreanAttrPrefix(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'korean = widechar.Korean()'
    ]
    cmd = 'print(korean.따르다)'
    cmd_tab_index = 14
    result = 'follow'
    tidy_cmd = ')'
    tidy_len = 1
    comp_len = 0
    comp_idx = None
    timeout = 3

class Completions_UTF8_KoreanDictKey(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'korean = widechar.Korean()'
    ]
    cmd = "print(korean.actions['담그다'])"
    cmd_tab_index = 23
    result = '1'
    tidy_cmd = ')'
    tidy_len = 1
    comp_len = 0
    comp_idx = None
    #comp = '1'
    timeout = 3

# need to get more keys which start with common "letters"
# class Completions_UTF8_KoreanDictKey2(CompletionsBase):
#     prep_script = [
#         'from editline.test.support import widechar',
#         'korean = widechar.Korean()'
#     ]
#     cmd = "print(korean.actions['????'])"
#     cmd_tab_index = 22
#     result = '1'
#     tidy_cmd = "ραλείπω'])"
#     tidy_len = 1
#     comp_len = 2
#     comp_idx = 0
#     comp_regexp = r'παίζω\s+παραλείπω'
#     timeout = 3


################################################################################
#
#  Test using Russian UTF8 Characters
#
################################################################################

class Completions_UTF8_RussianAttr(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'russian = widechar.Russian()'
    ]
    cmd = 'russian.__module__'
    cmd_tab_index = 8
    result = 'editline.test.support.widechar'
    tidy_cmd = None
    tidy_len = None
    comp_len = 4
    comp_idx = 1
    comp_regexp = r'russian.запах\s+russian.играть\s+russian.падение\s+russian.пропускать'
    timeout = 3

class Completions_UTF8_RussianAttrPrefix(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'russian = widechar.Russian()'
    ]
    cmd = 'print(russian.падение)'
    cmd_tab_index = 15
    result = 'dip'
    tidy_cmd = 'адение)'
    tidy_len = 1
    comp_len = 2
    comp_idx = 0
    comp_regexp = r'russian.падение\s+russian.пропускать'
    timeout = 3

class Completions_UTF8_RussianDictKey(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'russian = widechar.Russian()'
    ]
    cmd = "print(russian.actions['Прыгать'])"
    cmd_tab_index = 24
    result = '1'
    tidy_cmd = ')'
    tidy_len = 1
    comp_len = 0
    comp_idx = None
    timeout = 3

class Completions_UTF8_RussianDictKey2(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'russian = widechar.Russian()'
    ]
    cmd = "print(russian.actions['пропускать'])"
    cmd_tab_index = 24
    result = '1'
    tidy_cmd = "ропускать'])"
    tidy_len = 1
    comp_len = 2
    comp_idx = 0
    comp_regexp = r'падение\s+пропускать'
    timeout = 3


################################################################################
#
#  Test using Tamil UTF8 Characters
#
################################################################################

class Completions_UTF8_TamilAttr(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'tamil = widechar.Tamil()'
    ]
    cmd = 'tamil.__module__'
    cmd_tab_index = 6
    result = 'editline.test.support.widechar'
    tidy_cmd = None
    tidy_len = None
    comp_len = 4
    comp_idx = 1
    comp_regexp = r'tamil.பின்பற்ற\s+tamil.ரன்\s+tamil.ரோல்\s+tamil.வழிவகுக்கும்'
    timeout = 3

class Completions_UTF8_TamilAttrPrefix(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'tamil = widechar.Tamil()'
    ]
    cmd = 'print(tamil.விளையாட)'
    cmd_tab_index = 14
    result = 'play'
    tidy_cmd = None
    
    tidy_len = 1
    comp_len = 2
    comp_idx = 0
    comp_regexp = r'tamil.வழிவகுக்கும்\s+tamil.வாசனை\s+tamil.விளையாட'
    timeout = 3

class Completions_UTF8_TamilDictKey(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'tamil = widechar.Tamil()'
    ]
    cmd = "print(tamil.actions['தவிர்க்க'])"
    cmd_tab_index = 22
    result = '1'
    tidy_cmd = ')'
    tidy_len = 1
    comp_len = 0
    comp_idx = None
    timeout = 3

class Completions_UTF8_TamilDictKey2(CompletionsBase):
    prep_script = [
        'from editline.test.support import widechar',
        'tamil = widechar.Tamil()'
    ]
    cmd = "print(tamil.actions['வழிவகுக்கும்'])"
    cmd_tab_index = 22
    result = '1'
    tidy_cmd = "ழிவகுக்கும்'])"
    tidy_len = 1
    comp_len = 2
    comp_idx = 0
    comp_regexp = r'வழிவகுக்கும்\s+வாசனை\s+விளையாட'
    timeout = 3


    
if __name__ == "__main__":
    unittest.main()
