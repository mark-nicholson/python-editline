"""
Very minimal unittests for parts of the editline module.
"""
#from contextlib import ExitStack
#from errno import EIO
import os
#import selectors
#import subprocess
import sys
#import tempfile
import unittest
from test.support import import_module
#from test.support.script_helper import assert_python_ok


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
        

if __name__ == "__main__":
    unittest.main()
