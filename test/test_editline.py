"""
Unit testing for parts of the editline and _editline modules.
"""
import os
import sys
import unittest
import subprocess
from test.support import import_module

# too bad this thing moved ...
try:
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 5:
        from test.support.script_helper import assert_python_ok
    else:
        from test.script_helper import assert_python_ok
    have_assert_python_ok = True
except ImportError:
    have_assert_python_ok = False
    
def check_test_support():
    #try:
    #    from test.support.script_helper import assert_python_ok
    #    return True
    #except ImportError:
    #    pass

    #try:
    #    from test.script_helper import assert_python_ok
    #    return True
    #except ImportError:
    #    pass
    
    return have_assert_python_ok
    
class TestEditline(unittest.TestCase):

    def load_assert_python_ok(self):
        if sys.version_info[0] >= 3 and sys.version_info[1] >= 5:
            from test.support.script_helper import assert_python_ok
        else:
            from test.script_helper import assert_python_ok
    
    def test_001_import_1(self):
        _editline = import_module('_editline')

    def test_002_import_2(self):
        editline = import_module('editline')

    def test_003_build_instance(self):
        editline = import_module('editline')
        el = editline.editline("testcase",
                               sys.stdin, sys.stdout, sys.stderr)
        self.assertIsNotNone(el)

    @unittest.skipUnless(check_test_support(), "no script_helper")
    def test_100_import(self):
        self.load_assert_python_ok()
        #from test.support.script_helper import assert_python_ok
        rc, stdout, stderr = assert_python_ok('-c', 'import editline')
        self.assertEqual(stdout, b'')
        self.assertEqual(rc, 0)
    
    @unittest.skipUnless(check_test_support(), "no script_helper")
    def test_101_init(self):
        # Issue #19884: Ensure that the ANSI sequence "\033[1034h" is not
        # written into stdout when the readline module is imported and stdout
        # is redirected to a pipe.
        self.load_assert_python_ok()
        #from test.support.script_helper import assert_python_ok
        rc, stdout, stderr = assert_python_ok('-c', 'import editline',
                                              TERM='xterm-256color')
        self.assertEqual(stdout, b'')
        self.assertEqual(rc, 0)

    def test_200_terminal_size(self):
        rows = int(subprocess.check_output(['tput', 'lines']).decode())
        columns = int(subprocess.check_output(['tput', 'cols']).decode())

        self.assertNotEqual(columns, 0)

        editline = import_module('editline')
        el = editline.editline("testcase",
                               sys.stdin, sys.stdout, sys.stderr)
        el_cols = el.gettc('co')
        self.assertEqual(el_cols, columns)

if __name__ == "__main__":
    unittest.main()
