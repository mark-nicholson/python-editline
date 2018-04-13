"""
Very minimal unittests for parts of the lineeditor module.
"""
import sys
import os
import re
import unittest
from test.support import import_module


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

    expty = None

    def setUp(self):
        # fire up the test subject
        self.expty = import_module('editline.tests.expty')
        # should use sys.ps1 for the prompt, but it seems to only be define
        # when the system actually IS interactive... ?
        self.tool = self.expty.InteractivePTY(sys.executable, '>>> ', 'exit()')
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
    prep_script = []             # cmds to setup for test
    timeout = 1                  # seconds to wait for completion

    # tidy_ members are for how do recover the parser to a sane state
    tidy_cmd = None              # chars to complete a valid python cmd after tab
    tidy_len = None              # output line count from tidy command

    # comp* members are for how to check the 'completions'
    comp = 'in      input(  int(' # what should the answer be.
                                  #   - None means expect no completion at all
                                  #   - RegEx is also an option
    comp_idx = 0                 # in which output line
    comp_len = 2                 # number of output lines resulting from tab-complete

    dud_re = re.compile('^\s*$') # a bogus RE to check types
    
    def setUp(self):
        super().setUp()
        #print("DBG:CB.setUp():", self.cmd)
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

        # check the amount of output
        self.assertEqual(len(output), self.tidy_len,
                         "Final command should have {0:d} lines of output: {1}".format(self.tidy_len, str(output)))

        # if there is output, make sure the expected result is present
        if self.tidy_len > 0:
            self.assertIn(self.result, output[0],
                          "{0} not in {1}".format(self.result, output[0]))
        
        # mop up
        super().tearDown()

    def tidy_output(self, output):
        try:
            output.remove('\x1b[K')
        except ValueError:
            pass   # wasn't in the list
        return output

    def test_completion(self):
        try:
            # put in a partial command with at <tab>
            output = self.tool.cmd(
                self.cmd[:self.cmd_tab_index]+'\t',
                add_crlf=False,
                timeout=self.timeout
            )

            # scrub weirdness out of the output
            output = self.tidy_output(output)

            # verify the first part
            self.assertEqual(
                len(output), self.comp_len,
                "Completion output length mismatch:" + str(output))

            # identify the result is correct
            if self.comp is None:
                # shouldn't have any output
                self.assertEqual(len(output), 0, "Shouldn't have any completion output")

            elif isinstance(self.comp,str):
                self.assertIn(
                    self.comp, output[self.comp_idx],
                    "Failed to find '{0}' in '{1}'".format(self.comp,
                                                           output[self.comp_idx]))

            elif type(self.comp) is type(self.dud_re):
                self.assertRegex(
                    output[self.comp_idx], self.comp)

            else:
                self.fail("No comparison data configured")
            
        except self.expty.PtyTimeoutError:
            # a timeout can display nothing to complete...
            if self.comp is None:
                # we're good.  Timed-out waiting for no response.
                return
            # nope, really a problem, propagate it
            raise


class Completions_In_Regexp(CompletionsBase):
    comp = re.compile('in\s+input\(\s+int\(')

class Completions_Version(CompletionsBase):
    cmd = 'sys.version'
    cmd_tab_index = 7
    cmd_should_complete = True
    tidy_cmd = ''    # this cmd will complete correctly
    tidy_len = 1
    result = sys.version[:30]
    comp = re.compile(r'sys.version\s+sys.version_info')
    prep_script = [
        'import sys'
    ]


#
#   Check Global entities
#

class GlobalStringCompletions(CompletionsBase):
    ''''some-string'.\t   Should have string-ish completion options'''
    cmd = '"tomato".upper()'
    cmd_tab_index = 9
    result = 'TOMATO'
    comp = re.compile(r'"tomato".capitalize\(\s+"tomato".casefold\(\s+"tomato".center\(')
    comp_len = 16
    comp_idx = 0


class NoIntegerArgCompletions(CompletionsBase):
    '''int(12\t           Should have no completions...'''
    cmd_tab_index = 6
    comp = None         # NO completions expected

class NoStringArgCompletions(CompletionsBase):
    '''print('toma\t      Should have no completions...'''
    cmd = 'print("tomato")'
    cmd_tab_index = 10
    result = 'tomato'
    comp = None         # NO completions expected

#
#   Check attributes
#

# sys.version_info[0].\t     FAILS   (sys.version.\t   WORKS)


#
#  Check Call evaluation and flag setting
#

# hex(12).\t    -> should NOT complete anything by default
#               -> set lineeditor.allow_eval_of_call = True, then completion happens


#
#   Check Import statement completion
#

class Completions_Import(CompletionsBase):
    cmd = 'import sys'
    cmd_tab_index = 3
    tidy_cmd = ' sys'
    tidy_len = 0
    comp = None
    comp_len = 0
    timeout = 10


class Completions_ImportSys(Completions_Import):
    cmd_tab_index = 9
    tidy_cmd = None
    tidy_len = 0
    comp_idx = 0
    comp_len = 2
    comp = re.compile(r'symbol\s+symtable\s+sys\s+sysconfig\s+syslog')

class Completions_FromImport(CompletionsBase):
    cmd = 'from os import path'
    cmd_tab_index = 3
    tidy_cmd = None
    tidy_len = 0
    comp_idx = 0
    comp_len = 2
    comp = re.compile(r'from\s+frozenset\(')

class Completions_FromImport_Fill(CompletionsBase):
    cmd = 'from os import path'
    cmd_tab_index = 2
    tidy_cmd = cmd[3:]          # system should auto-add the 'o'
    tidy_len = 0
    comp_idx = 0
    comp_len = 2
    comp = re.compile(r'from\s+frozenset\(')


if __name__ == "__main__":
    unittest.main()
