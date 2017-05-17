"""
Very minimal unittests for parts of the lineeditor module.
"""
from contextlib import ExitStack
from errno import EIO
import os
import selectors
import subprocess
import sys
import tempfile
import unittest
from test.support import import_module, unlink, TESTFN
from test.support.script_helper import assert_python_ok


class TestEditLineCompleter(unittest.TestCase):

    def test_import(self):
        rc, stdout, stderr = assert_python_ok('-c', 'import editline')
        self.assertEqual(stdout, b'')
        self.assertEqual(rc, 0)
    
    def test_init(self):
        # Issue #19884: Ensure that the ANSI sequence "\033[1034h" is not
        # written into stdout when the readline module is imported and stdout
        # is redirected to a pipe.
        rc, stdout, stderr = assert_python_ok('-c', 'import editline',
                                              TERM='xterm-256color')
        self.assertEqual(stdout, b'')
        self.assertEqual(rc, 0)


class TestEditLineCompleterBase(unittest.TestCase):

    instance_cmds = [
        'import sys',
        'from editline import editline',
        'from lineeditor import EditlineCompleter',
        'el = editline("shim", sys.stdin, sys.stdout, sys.stderr)',
        'lec = EditlineCompleter(el)',
        'el.completer = lec.complete'
        ]

    global_cmds = [
        'import _editline',
        'gi = _editline.get_global_instance()'
        ]

    def setUp(self):
        # fire up the test subject
        expty = import_module('expty')
        # should use sys.ps1 for the prompt, but it seems to only be define
        # when the system actually IS interactive... ?
        self.tool = expty.InteractivePTY(sys.executable, '>>> ', 'exit()')
        cruft = self.tool.first_prompt()

    def tearDown(self):
        self.tool.close()


class TestEditLineCompleterInstance(TestEditLineCompleterBase):

    def test_001_load(self):
        for cmd in self.instance_cmds:
            output = self.tool.cmd(cmd)
            self.assertEqual(len(output), 0)

    def test_002_el_type(self):
        self.tool.run_script(self.instance_cmds)
        output = self.tool.cmd('print(str(type(el)))')
        self.assertEqual(len(output), 1)
        self.assertIn("<class 'editline.editline'>", output[0])

    def test_002_lec_type(self):
        self.tool.run_script(self.instance_cmds)
        output = self.tool.cmd('print(str(type(lec)))')
        self.assertEqual(len(output), 1)
        self.assertIn("<class 'lineeditor.EditlineCompleter'>", output[0])


class TestEditLineCompleterGlobal(TestEditLineCompleterBase):

    def test_001_load(self):
        for cmd in self.global_cmds:
            output = self.tool.cmd(cmd)
            self.assertEqual(len(output), 0)

    def test_002_el_type(self):
        self.tool.run_script(self.global_cmds)
        output = self.tool.cmd('print(str(type(gi)))')
        self.assertEqual(len(output), 1)
        self.assertIn("<class 'editline.editline'>", output[0])

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
        self.assertIn("<class 'editline.editline'>", output[0])

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


if __name__ == "__main__":
    unittest.main()
