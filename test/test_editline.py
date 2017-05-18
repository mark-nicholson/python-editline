"""
Unit testing for parts of the editline and _editline modules.
"""
import os
import sys
import unittest
import subprocess
from test.support import import_module
from test.support.script_helper import assert_python_ok


class TestEditline(unittest.TestCase):

    def test_001_import_1(self):
        _editline = import_module('_editline')

    def test_002_import_2(self):
        editline = import_module('editline')

    def test_003_build_instance(self):
        editline = import_module('editline')
        el = editline.editline("testcase",
                               sys.stdin, sys.stdout, sys.stderr)
        self.assertIsNotNone(el)
        
    def test_100_import(self):
        rc, stdout, stderr = assert_python_ok('-c', 'import editline')
        self.assertEqual(stdout, b'')
        self.assertEqual(rc, 0)
    
    def test_101_init(self):
        # Issue #19884: Ensure that the ANSI sequence "\033[1034h" is not
        # written into stdout when the readline module is imported and stdout
        # is redirected to a pipe.
        rc, stdout, stderr = assert_python_ok('-c', 'import editline',
                                              TERM='xterm-256color')
        self.assertEqual(stdout, b'')
        self.assertEqual(rc, 0)

    def test_200_terminal_size(self):
        rows, columns = subprocess.check_output(['stty', 'size']).decode().split()
        self.assertNotEqual(int(columns), 0)

        editline = import_module('editline')
        el = editline.editline("testcase",
                               sys.stdin, sys.stdout, sys.stderr)
        el_cols = el.gettc('co')
        self.assertEqual(el_cols, int(columns))

if __name__ == "__main__":
    unittest.main()
