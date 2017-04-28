"""
Very minimal unittests for parts of the editline module.
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


class TestEditline(unittest.TestCase):

    def test_import_1(self):
        _editline = import_module('_editline')

    def test_import_2(self):
        editline = import_module('editline')

    def test_build_instance(self):
        editline = import_module('editline')
        el = editline.editline("testcase",
                               sys.stdin, sys.stdout, sys.stderr)
        self.assertIsNotNone(el)
        

class TestEditlineConsole(unittest.TestCase):

    base_init_script = r"""import sys
import editline
import lineeditor

el = editline.editline("shim", sys.stdin, sys.stdout, sys.stderr)
lec = lineeditor.Completer(editor_support=el)
el.completer = lec.complete
"""
    
    gi_script = r"""
import _editline
gi = _editline.get_global_instance()
"""
    
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


    def test_setup_instance(self):
        output = run_pty(self.base_init_script)
        self.assertIn(b"\r\n", output)

    def test_basic_readline(self):
        script = self.base_init_script + r"""
s = el.readline()
print(s)
"""
        in_cmd = b"print('hello')"
        input_str = in_cmd + b"\r" 
        io = run_pty(script, input_str)
        output = io[len(input_str):]    # trim off the input chars
        self.assertIn(in_cmd, output)
        self.assertEqual(output.count(in_cmd), 2) # cmd and result

    def test_basic_completion(self):
        script = self.base_init_script + r"""
el.rprompt = '<RP'
s = el.readline()
print(s)
"""
        input = b"in\t\n"
        io = run_pty(script, input)
        output = io[len(input):]
        self.assertIn(b"in      input(  int(", output)

#     def test_global_instance_valid(self):
#         script = self.gi_script + r"""
# print(str(gi is None))
# """
#         output = run_pty(script, b"")
#         self.assertIn(b"False", output)

#     def test_global_instance_type(self):
#         script = self.gi_script + r"""
# print(str(type(gi)))
# exit()
# """
#         output = run_pty_i(script, b"")
#         self.assertIn(b"<class 'ediline.editline'>", output)

    def test_right_prompt(self):
        rprompt = b'<RP'
        script = self.base_init_script + r"""
el.rprompt = '<RP'
s = el.readline()
print(s)
"""
        input = b"bogus chars\n"
        io = run_pty(script, input)
        output = io[len(input):]
        lines = output.split(b'\r')
        self.assertIn(rprompt, output)
        for i,line in enumerate(lines):
            if line.startswith(b'EL>'):
                self.assertTrue(line.endswith(rprompt))

def run_pty(script, input=b"dummy input\r"):
    pty = import_module('pty')
    output = bytearray()
    [master, slave] = pty.openpty()
    args = (sys.executable, '-c', script)
    proc = subprocess.Popen(args, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    with ExitStack() as cleanup:
        cleanup.enter_context(proc)
        def terminate(proc):
            try:
                proc.terminate()
            except ProcessLookupError:
                # Workaround for Open/Net BSD bug (Issue 16762)
                pass
        cleanup.callback(terminate, proc)
        cleanup.callback(os.close, master)
        # Avoid using DefaultSelector and PollSelector. Kqueue() does not
        # work with pseudo-terminals on OS X < 10.9 (Issue 20365) and Open
        # BSD (Issue 20667). Poll() does not work with OS X 10.6 or 10.4
        # either (Issue 20472). Hopefully the file descriptor is low enough
        # to use with select().
        sel = cleanup.enter_context(selectors.SelectSelector())
        sel.register(master, selectors.EVENT_READ | selectors.EVENT_WRITE)
        os.set_blocking(master, False)
        while True:
            for [_, events] in sel.select():
                if events & selectors.EVENT_READ:
                    try:
                        chunk = os.read(master, 0x10000)
                    except OSError as err:
                        # Linux raises EIO when slave is closed (Issue 5380)
                        if err.errno != EIO:
                            raise
                        chunk = b""
                    if not chunk:
                        return output
                    output.extend(chunk)
                if events & selectors.EVENT_WRITE:
                    try:
                        input = input[os.write(master, input):]
                    except OSError as err:
                        # Apparently EIO means the slave was closed
                        if err.errno != EIO:
                            raise
                        input = b""  # Stop writing
                    if not input:
                        sel.modify(master, selectors.EVENT_READ)


def run_pty_i(script, input=b"dummy input\r"):
    pty = import_module('pty')
    output = bytearray()
    [master, slave] = pty.openpty()
    args = (sys.executable, '-i', '-c', script)
    proc = subprocess.Popen(args, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    with ExitStack() as cleanup:
        cleanup.enter_context(proc)
        def terminate(proc):
            try:
                proc.terminate()
            except ProcessLookupError:
                # Workaround for Open/Net BSD bug (Issue 16762)
                pass
        cleanup.callback(terminate, proc)
        cleanup.callback(os.close, master)
        # Avoid using DefaultSelector and PollSelector. Kqueue() does not
        # work with pseudo-terminals on OS X < 10.9 (Issue 20365) and Open
        # BSD (Issue 20667). Poll() does not work with OS X 10.6 or 10.4
        # either (Issue 20472). Hopefully the file descriptor is low enough
        # to use with select().
        sel = cleanup.enter_context(selectors.SelectSelector())
        sel.register(master, selectors.EVENT_READ | selectors.EVENT_WRITE)
        os.set_blocking(master, False)
        while True:
            for [_, events] in sel.select():
                if events & selectors.EVENT_READ:
                    try:
                        chunk = os.read(master, 0x10000)
                    except OSError as err:
                        # Linux raises EIO when slave is closed (Issue 5380)
                        if err.errno != EIO:
                            raise
                        chunk = b""
                    if not chunk:
                        return output
                    output.extend(chunk)
                if events & selectors.EVENT_WRITE:
                    try:
                        input = input[os.write(master, input):]
                    except OSError as err:
                        # Apparently EIO means the slave was closed
                        if err.errno != EIO:
                            raise
                        input = b""  # Stop writing
                    if not input:
                        sel.modify(master, selectors.EVENT_READ)


if __name__ == "__main__":
    unittest.main()
