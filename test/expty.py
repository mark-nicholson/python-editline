
import sys
import os
import time
from errno import EIO
import pty
import subprocess
import selectors

class InteractivePTY(object):

    def __init__(self, tool, prompt, exit_cmd, args=[], encoding='UTF-8'):
        self._tool = tool
        self._tool_args = args
        self._prompt = prompt
        self._encoding = encoding
        self._exit_cmd = exit_cmd
        
        # where to accumulate incoming data
        self._raw_buffer = b''

        # cook up a PTY
        self.master, self.slave = pty.openpty()

        # hook it up to a subprocess
        args = [ self._tool ] + self._tool_args
        self.proc = subprocess.Popen(args,
                                     stdin=self.slave,
                                     stdout=self.slave,
                                     stderr=self.slave)

        # register a selector manager
        self.sel = selectors.SelectSelector()
        self.sel.register(self.master,
                          selectors.EVENT_READ | selectors.EVENT_WRITE)

        # try to avoid os interference
        os.set_blocking(self.master, False)
        
    def __del__(self):
        # normally, this is not necessary, but this class could have
        # a bunch of dangling resources.
        if self.proc:
            try:
                self.proc.kill()
            except ProcessLookupError:
                # Workaround for Open/Net BSD bug (Issue 16762)
                pass
        if self.master:
            os.close(self.master)
        if self.slave:
            os.close(self.slave)

    def close(self):
        r = self.cmd(self._exit_cmd)
        self.proc_rc = self.proc.wait()

    def get_data(self, marker='\n', timeout=0):

        # the data is managed as bytes
        marker = marker.encode(self._encoding)
        
        # do we already have it?
        tok, predata, self._raw_buffer = self._parse_marker(marker,
                                                            self._raw_buffer)
        if tok == marker:
            return tok.decode(self._encoding), predata.decode(self._encoding)

        # remember when we begin
        end_time = time.time() + timeout
        
        # nope, rummage for more data
        while True:
            for [_, events] in self.sel.select(timeout):
                if events & selectors.EVENT_READ:
                    try:
                        chunk = os.read(self.master, 0x10000)
                    except OSError as err:
                        # Linux raises EIO when slave is closed (Issue 5380)
                        if err.errno != EIO:
                            raise
                        chunk = b""

                    if chunk is None:
                        continue

                    elif chunk == b'':
                        continue

                    else:
                        # remember it
                        self._raw_buffer += chunk  #.decode(self._encoding)

                        # check for the marker
                        tok, predata, self._raw_buffer = self._parse_marker(marker, self._raw_buffer)
                        if tok == marker:
                            return tok.decode(self._encoding), predata.decode(self._encoding)
                else:
                    # bailout if the timeout has exceeded
                    if end_time < time.time():
                        return None, None

    def _parse_marker(self, marker, data):
        try:
            predata, data = data.split(marker, 1)
        except ValueError:
            # no marker ...
            marker = None
            predata = None

        return marker, predata, data

    def send_data(self, data, add_crlf=True):
        retries = 5
        
        # most interpreters want a newline
        if add_crlf:
            data += '\n'

        # switch to the target encoding
        bdata = data.encode(self._encoding)

        # chug until we've written our data
        while True:
            for [_, events] in self.sel.select():
                if events & selectors.EVENT_WRITE:
                    try:
                        bdata = bdata[os.write(self.master, bdata):]
                    except OSError as err:
                        # Apparently EIO means the slave was closed
                        if err.errno != EIO:
                            raise

                    # return unwritten data. '' means everything went...
                    return bdata.decode(self._encoding)
                else:
                    # try a bit harder -- wait a bit for the buffer to drain
                    if len(bdata) > 0 and retries > 0:
                        time.sleep(0.1)
                        retries -= 1
                        continue

                    # bail out, can write no more
                    return ''

    def first_prompt(self):
        # collect initial output
        p,d = self.get_data(self._prompt, 1)

        # got it...
        if p is not None:
            return d

        # no prompt? snooze a bit and retry
        time.sleep(0.1)
        p,d = self.get_data(self._prompt, 1)
        return d
        
    def sync_prompt(self):
        save_raw_buffer = self._raw_buffer
        self._raw_buffer = b''

        # poke it a few times...
        tries = 5
        while tries > 0:
            tries -= 1
            self.send_data('\n')
            p,d = self.get_data(self.prompt, 0.1)
            if p == self.prompt:
                return True

        # hmm. dead?
        return False
            

    def cmd(self, cmd, marker=None, as_string=False, timeout=1, trim_cmd=True, add_crlf=True):
        if marker is None:
            marker = self._prompt

        # clear out any accumulated cruft
        while True:
            prompt,d = self.get_data(marker, timeout=0)
            if prompt is None:
                break

        # fire off the instruction
        self.send_data(cmd, add_crlf)

        # collect the result
        prompt, data = self.get_data(marker, timeout=timeout)

        # return it as requested
        if as_string:
            return data

        if data is None:
            return []

        lines = data.splitlines()
        if trim_cmd:
            lines.pop(0)

        return lines

    def run_script(self, script):

        # scripts should be run one line at a time
        if type(script) is str:
            cmds = script.split(os.linesep)
        else:
            cmds = script

        # want to collect all the output in one go
        output = []

        # iterate them 
        for cmd in cmds:
            r = self.cmd(cmd)
            output.extend(r)

        # done
        return output
