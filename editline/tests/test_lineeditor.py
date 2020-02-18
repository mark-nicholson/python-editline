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
        'from editline.editline import EditLine',
        'from editline.lineeditor import EditlineCompleter',
        'el = EditLine("shim", sys.stdin, sys.stdout, sys.stderr)',
        'lec = EditlineCompleter(el)',
        'el.completer = lec.complete'
        ]

    global_cmds = [
        'from editline import _editline',
        'gi = _editline.get_global_instance()'
        ]

    editline_class_pstr = "<class 'editline.editline.EditLine'>"
    lineeditor_class_pstr = "<class 'editline.lineeditor.EditlineCompleter'>"

    expty = None

    def setUp(self):
        #print("DBG:CB.setUp()")
        # fire up the test subject
        self.expty = import_module('editline.tests.expty')
        # should use sys.ps1 for the prompt, but it seems to only be define
        # when the system actually IS interactive... ?
        self.tool = self.expty.InteractivePTY(sys.executable, '>>> ', 'exit()')
        cruft = self.tool.first_prompt()

    def tearDown(self):
        #print("DBG:CB.tearDown()")
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

    def test_006_big_command_support(self):
        self.tool.run_script(self.global_cmds)
        data = [x for x in range(1000)]
        cmd = 'tomato = ' + str(data)
        try:
            output = self.tool.cmd(cmd)
            self.assertEqual(len(output), 0)
        except self.expty.PtyTimeoutError as cm:
            self.fail("big-command crashed the interpreter")


class CompletionsAbstractBase(CompleterBase):

    cmd = ''                     # whole python command
    cmd_tab_index = 0            # where to break it and insert a '\t'
    result = ''                  # what the actual command yields
    result_idx = 0               # what line to expect this result
    
    prep_script = []             # cmds to setup for test
    timeout = 1                  # seconds to wait for completion

    # tidy_ members are for how do recover the parser to a sane state
    tidy_cmd = None              # chars to complete a valid python cmd after tab
    tidy_len = None              # output line count from tidy command

    # comp* members are for how to check the 'completions'
    comp = None                  # what should the answer be.
                                 #   - None means expect no completion at all
                                 #   - RegEx is also an option
    comp_idx = 0                 # in which output line
    comp_len = 0                 # number of output lines resulting from tab-complete

    dud_re = re.compile('^\s*$') # a bogus RE to check types
    
    def setUp(self):
        super().setUp()
        #print("DBG:CB.setUp():", self.cmd)
        
        # get the basics in place
        self.tool.run_script(self.global_cmds)

        # make sure editline is the global completer
        output = self.tool.cmd('print(str(type(gi)))')
        self.assertIn(self.editline_class_pstr, output[0])

        # run the prep commands
        if len(self.prep_script) > 0:
            self.tool.run_script(self.prep_script)

    def tearDown(self):
        # if nothing set, force a cleanup cmd
        if self.tidy_cmd is None:
            self.tidy_cmd = self.cmd[self.cmd_tab_index:]
        if self.tidy_len is None:
            self.tidy_len = 1

        # ensure we don't expect any output when no result is expected
        #if self.result is None:
        #    sys.stderr.write("DBG" + "flag\n")
        #    self.tidy_len = 0

        # we MUST complete the command or the exit support will be borked
        output = self.tool.cmd(self.tidy_cmd)
        output = self._tidy_output(output)

        # check the amount of output
        self.assertEqual(len(output), self.tidy_len,
                         "Final command should have {0:d} lines of output: {1}".format(self.tidy_len, str(output)))

        # if there is output, make sure the expected result is present
        if self.result is not None and self.tidy_len > 0:
            self.assertIn(self.result, output[self.result_idx],
                          "{0} not in {1}".format(self.result, output[self.result_idx]))
        
        # mop up
        super().tearDown()

    def do_completion_test(self):
        '''This is the testing infrastructure, but setup to call it more than once.'''
        #print(os.linesep +  '    {0}\\t'.format(self.cmd[:self.cmd_tab_index]))

        try:
            # put in a partial command with at <tab>
            output = self.tool.cmd(
                self.cmd[:self.cmd_tab_index]+'\t',
                add_crlf=False,
                timeout=self.timeout
            )

            # scrub weirdness out of the output
            output = self._tidy_output(output)

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
                    "Failed to find '{0}' in '{1}'".format(
                        self.comp,
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

    def _tidy_output(self, output):
        try:
            output.remove('\x1b[K')
        except ValueError:
            pass   # wasn't in the list
        return output

class CompletionsBase(CompletionsAbstractBase):

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

    def test_001_basic(self):
        self.do_completion_test()


class CompletionsCommon(CompletionsBase):

    def test_002_call(self):
        prefix = 'print('
        self.cmd = prefix + self.cmd + ')'
        self.cmd_tab_index = self.cmd_tab_index + len(prefix)

        # update tidy cmd when tab-completion is successful
        if self.tidy_cmd is not None:
            self.tidy_cmd = self.tidy_cmd + ')'

        # run the basic engine
        self.do_completion_test()

    def test_002_call_w_space(self):
        prefix = 'print( '
        self.cmd = prefix + self.cmd + ')'
        self.cmd_tab_index = self.cmd_tab_index + len(prefix)

        # update tidy cmd when tab-completion is successful
        if self.tidy_cmd is not None:
            self.tidy_cmd = self.tidy_cmd + ')'

        # run the basic engine
        self.do_completion_test()

    def test_003_assignment(self):
        prefix = 'x='
        self.cmd = prefix + self.cmd
        self.cmd_tab_index = self.cmd_tab_index + len(prefix)
        self.result = None
        self.tidy_len = 0

        # run the basic engine
        self.do_completion_test()

    def test_003_assignment_w_space(self):
        prefix = 'x = '
        self.cmd = prefix + self.cmd
        self.cmd_tab_index = self.cmd_tab_index + len(prefix)
        self.result = None
        self.tidy_len = 0

        # run the basic engine
        self.do_completion_test()

    def test_004_call_call(self):
        prefix = 'print(str('
        self.cmd = prefix + self.cmd + '))'
        self.cmd_tab_index = self.cmd_tab_index + len(prefix)

        # update tidy cmd when tab-completion is successful
        if self.tidy_cmd is not None:
            self.tidy_cmd = self.tidy_cmd + '))'

        # run the basic engine
        self.do_completion_test()

    def test_004_call_ws_call(self):
        prefix = 'print( str('
        self.cmd = prefix + self.cmd + '))'
        self.cmd_tab_index = self.cmd_tab_index + len(prefix)

        # update tidy cmd when tab-completion is successful
        if self.tidy_cmd is not None:
            self.tidy_cmd = self.tidy_cmd + '))'

        # run the basic engine
        self.do_completion_test()

    def test_004_call_ws_call_ws(self):
        prefix = 'print( str( '
        self.cmd = prefix + self.cmd + '))'
        self.cmd_tab_index = self.cmd_tab_index + len(prefix)

        # update tidy cmd when tab-completion is successful
        if self.tidy_cmd is not None:
            self.tidy_cmd = self.tidy_cmd + '))'

        # run the basic engine
        self.do_completion_test()

        
class Completions_In_Regexp(CompletionsBase):
    comp = re.compile('in\s+input\(\s+int\(')

class Completions_Version(CompletionsBase):
    cmd = 'sys.version'
    cmd_tab_index = 7
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

    def setUp(self):
        # a new string routine was added in 3.7
        if sys.version_info[1] >=7:
            self.comp_len += 1
        super().setUp()


class NoIntegerArgCompletions(CompletionsBase):
    '''int(12\t           Should have no completions...'''
    cmd_tab_index = 6
    comp = None         # NO completions expected
    result = '12'
    result_idx = 1
    tidy_len = 2
    #tidy_cmd = ''
    comp_len = 0

class NoStringArgCompletions(CompletionsBase):
    '''print('toma\t      Should have no completions...'''
    cmd = 'print("tomato")'
    cmd_tab_index = 10
    result = 'tomato'
    result_idx = 1
    comp = None         # NO completions expected
    tidy_len = 2
    comp_len = 0

#
#   Check attributes
#

class Completions_ClassWith__getitem__(CompletionsBase):
    '''sys.version_info is a class which implements __getitem__'''
    prep_script = [
        'import sys'
    ]
    cmd = 'sys.version_info[0]'
    cmd_tab_index = 17
    result = '3'
    comp = re.compile(r'0\s+1\s+2\s+3\s+4')
    comp_idx = 0
    comp_len = 2


#
#  Check Call evaluation and flag setting
#

class Completions_CallInExpr(CompletionsBase):
    '''hex(12).\t    -> should NOT complete anything by default'''
    cmd = 'hex(12).upper()'
    cmd_tab_index = 8
    result = '0xc'
    result_idx = 2
    tidy_cmd = '\b'
    tidy_len = 3
    comp = None

class Completions_CallInExpr_FlagOk(Completions_CallInExpr):
    '''hex(12).\t    -> should provide completions as if it were a string'''
    prep_script = [
        'from editline import lineeditor',
        'gle = lineeditor.global_line_editor()',
        'gle.allow_eval_of_calls = True'
    ]
    cmd = 'hex(12).upper()'
    result = '0XC'
    result_idx = 0
    tidy_cmd = None
    tidy_len = None
    comp = re.compile(r'hex\(12\).capitalize\(\s+hex\(12\).casefold\(\s+hex\(12\).center\(')
    comp_idx = 0
    comp_len = 16

    def setUp(self):
        # a new string routine was added in 3.7
        if sys.version_info[1] >=7:
            self.comp_len += 1
        super().setUp()


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
