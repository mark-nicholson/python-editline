"""
Very minimal unittests for parts of the lineeditor module.
"""
from contextlib import ExitStack
from errno import EIO
import os
import subprocess
import sys
import re
import tempfile
import unittest
from test.support import import_module, unlink, TESTFN


class CompleterBase(unittest.TestCase):

    instance_cmds = [
        'import sys',
        'from editline.editline import editline',
        'from editline.lineeditor import EditlineCompleter',
        'el = editline("shim", sys.stdin, sys.stdout, sys.stderr)',
        'lec = EditlineCompleter(el)',
        'el.completer = lec.complete'
        ]

    global_cmds = [
        'from editline import _editline',
        'gi = _editline.get_global_instance()'
        ]

    editline_class_pstr = "<class 'editline.editline.editline'>"
    lineeditor_class_pstr = "<class 'editline.lineeditor.EditlineCompleter'>"

    def setUp(self):
        # fire up the test subject
        expty = import_module('expty')
        # should use sys.ps1 for the prompt, but it seems to only be define
        # when the system actually IS interactive... ?
        self.tool = expty.InteractivePTY(sys.executable, '>>> ', 'exit()')
        cruft = self.tool.first_prompt()

    def tearDown(self):
        self.tool.close()


class InstanceCompleter(CompleterBase):

    def test_001_load(self):
        for cmd in self.instance_cmds:
            output = self.tool.cmd(cmd)
            self.assertEqual(len(output), 0)

    def test_002_el_type(self):
        self.tool.run_script(self.instance_cmds)
        output = self.tool.cmd('print(str(type(el)))')
        self.assertEqual(len(output), 1)
        self.assertIn(self.editline_class_pstr, output[0])

    def test_002_lec_type(self):
        self.tool.run_script(self.instance_cmds)
        output = self.tool.cmd('print(str(type(lec)))')
        self.assertEqual(len(output), 1)
        self.assertIn(self.lineeditor_class_pstr, output[0])


class GlobalCompleter(CompleterBase):

    def test_001_load(self):
        for cmd in self.global_cmds:
            output = self.tool.cmd(cmd)
            self.assertEqual(len(output), 0)

    def test_002_el_type(self):
        self.tool.run_script(self.global_cmds)
        output = self.tool.cmd('print(str(type(gi)))')
        self.assertEqual(len(output), 1)
        self.assertIn(self.editline_class_pstr, output[0])

    def test_003_basic_readline(self):
        txt = "provide input to readline"

        self.tool.run_script(self.instance_cmds)
        self.tool.cmd('s = el.readline()', marker='EL> ')
        self.tool.cmd(txt)
        output = self.tool.cmd('print(s)')
        self.assertEqual(len(output), 2)
        self.assertIn(txt, output[0])

    def test_004_basic_completion(self):
        self.tool.run_script(self.global_cmds)

        # make sure editline is the global completer
        output = self.tool.cmd('print(str(type(gi)))')
        self.assertIn(self.editline_class_pstr, output[0])

        # put in a partial command with at <tab>
        output = self.tool.cmd("in\t", add_crlf=False)
        self.assertEqual(len(output), 3)
        self.assertIn("in      input(  int(", output[0])

        # we MUST complete the command or the exit support will be borked
        output = self.tool.cmd('t("12")')
        self.assertEqual(len(output), 1)
        self.assertIn("12", output[0])

    def test_005_right_prompt(self):
        txt = "provide input to readline"
        rprompt = '<RP'

        # basic setup
        self.tool.run_script(self.instance_cmds)

        # collect some info
        output = self.tool.cmd('print(el.gettc("co"))')
        self.assertEqual(len(output), 1)
        cols = int(output[0])

        # configure the right-prompt string 
        output = self.tool.cmd('el.rprompt = "{}"'.format(rprompt))
        self.assertEqual(len(output), 0)

        # do a readline
        self.tool.cmd('s = el.readline()', marker='EL> ')
        output = self.tool.cmd(txt, trim_cmd=False)

        # verify the right prompt appears
        self.assertIn(rprompt, output[0])

        # verify that the right-prompt is actually on the right
        pos = output[0].find(rprompt) + len(rprompt) + len(self.tool._prompt)
        self.assertEqual(pos+1, cols)

        # make sure the basic command still works
        output = self.tool.cmd('print(s)')
        self.assertEqual(len(output), 2)
        self.assertIn(txt, output[0])


class CompletionsBase(CompleterBase):

    cmd = 'int(12)'              # whole python command
    cmd_tab_index = 2            # where to break it and insert a '\t'
    result = '12'                # what the actual command yields
    tidy_cmd = None
    tidy_len = None
    comp = 'in      input(  int(' # what should the answer be
    comp_regexp = None           # need regexp to really see if it matches
    comp_idx = 0                 # in which output line
    comp_len = 2                 # how much spew to expect
    prep_script = []             # cmds to setup for test
    timeout = 10                 # seconds to wait for completion
    
    def setUp(self):
        super().setUp()

        # if nothing set, force a cleanup cmd
        if self.tidy_cmd is None:
            self.tidy_cmd = self.cmd[self.cmd_tab_index:]
        if self.tidy_len is None:
            self.tidy_len = 1
        
        # get the basics in place
        self.tool.run_script(self.global_cmds)

        # make sure editline is the global completer
        output = self.tool.cmd('print(str(type(gi)))')
        self.assertIn(self.editline_class_pstr, output[0])

        # run the prep commands
        if len(self.prep_script) > 0:
            self.tool.run_script(self.prep_script)

    def tearDown(self):
        # we MUST complete the command or the exit support will be borked
        output = self.tool.cmd(self.tidy_cmd)
        output = self.tidy_output(output)
        if len(output) != self.tidy_len:
            print("DBG:", output)
        self.assertEqual(len(output), self.tidy_len)
        if self.tidy_len > 0:
            self.assertIn(self.result, output[0])
        
        # mop up
        super().tearDown()

    def tidy_output(self, output):
        try:
            output.remove('\x1b[K')
        except ValueError:
            pass   # wasn't in the list
        return output

    def test_completion(self):
        # put in a partial command with at <tab>
        output = self.tool.cmd(
            self.cmd[:self.cmd_tab_index]+'\t',
            add_crlf=False,
            timeout=self.timeout
        )
        output = self.tidy_output(output)
        if len(output) != self.comp_len:
            print("DBG:", output)
        self.assertEqual(len(output), self.comp_len)

        # no output to match
        if self.comp_idx is None:
            return
        
        # identify the result is correct
        if self.comp_regexp:
            self.assertRegex(output[self.comp_idx], self.comp_regexp)
        else:
            self.assertIn(self.comp, output[self.comp_idx])


class Completions_In_Regexp(CompletionsBase):
    comp = ''
    comp_regexp = re.compile('in\s+input\(\s+int\(')

class Completions_Version(CompletionsBase):
    cmd = 'sys.version'
    cmd_tab_index = 7
    cmd_should_complete = True
    tidy_cmd = ''    # this cmd will complete correctly
    tidy_len = 1
    result = sys.version[:30]
    comp = ''
    comp_regexp = re.compile(r'sys.version\s+sys.version_info')
    prep_script = [
        'import sys'
        ]

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
    tidy_cmd = '\b\b\b'
    tidy_len = 0

class Completions_FrozenSet(Completions_Set):
    prep_script = [
        'a = frozenset(range(1,21))'
        ]

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


#
#   Check Import statement completion
#

class Completions_Import(CompletionsBase):
    cmd = 'import sys'
    cmd_tab_index = 3
    tidy_cmd = ' sys'
    tidy_len = 0
    comp_idx = None
    comp_len = 0


class Completions_ImportSys(Completions_Import):
    cmd_tab_index = 9
    tidy_cmd = None
    tidy_len = 0
    comp_idx = 0
    comp_len = 2
    comp_regexp = re.compile(r'symbol\s+symtable\s+sys\s+sysconfig\s+syslog')

class Completions_FromImport(CompletionsBase):
    cmd = 'from os import path'
    cmd_tab_index = 3
    tidy_cmd = None
    tidy_len = 0
    comp_idx = 0
    comp_len = 2
    comp_regexp = re.compile(r'from\s+frozenset\(')

class Completions_FromImport_Fill(CompletionsBase):
    cmd = 'from os import path'
    cmd_tab_index = 2
    tidy_cmd = cmd[3:]          # system should auto-add the 'o'
    tidy_len = 0
    comp_idx = 0
    comp_len = 2
    comp_regexp = re.compile(r'from\s+frozenset\(')


if __name__ == "__main__":
    unittest.main()
