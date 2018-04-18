"""
Editline:
   Module to provide higher level functionality access to libedit.
"""

import sys
import os
from editline import _editline

class editline(_editline.EditLine):
    """Editline High Level Support
    Provides the usable interface to the _editline compiled module. This class
    is derived from the compiled module and it provides functionality which
    is best implemented in python code -- not C.
    """

    def __init__(self, name, in_stream, out_stream, err_stream):
        #print("EL.__init__: begin")

        # verify streams have fileno()
        if ("fileno" not in dir(in_stream) or
                "fileno" not in dir(out_stream) or
                "fileno" not in dir(err_stream)):
            raise Exception("Streams must have fileno()")

        # remember
        self.in_stream = in_stream
        self.out_stream = out_stream
        self.err_stream = err_stream

        # setup the parent
        super().__init__(name, in_stream, out_stream, err_stream)

        # hooks
        self.rl_completer = None
        self.completer = None
        self.display_matches = self._display_matches

    def parse_and_bind(self, cmd):
        """Create the translation between "readline" and "bind" """
        key, routine = cmd.split(':')

        keymap = {
            'tab': ['^I'],
        }

    def _completer(self, text):
        """Intermediate completer.  Handles the variations between the
        readline-way of doing things and just handing back the strings
        """
        # readline way of doing this...
        if self.rl_completer:
            exact = 'bogus'
            state = 0
            matches = []
            while True:
                exact = self.rl_completer(text, state)
                if exact is None:
                    break
                matches.append(exact)
                state += 1

        elif self.completer:
            matches = self.completer(text)
        else:
            # hmm. no completion support ?
            matches = []

        if len(matches) == 0:
            return _editline.CC_REFRESH

        if len(matches) == 1:
            self.insert_text(matches[0][len(text):])
            return _editline.CC_REDISPLAY

        # a selection...
        self.display_matches(matches)

        # find longest common prefix
        prefix = os.path.commonprefix(matches)
        plen = len(prefix)

        # may need to wedge in a couple chars
        if plen > len(text):
            self.insert_text(matches[0][len(text):plen])

        return _editline.CC_REDISPLAY

    def _display_matches(self, matches):
        sys.stdout.write('\n')

        # alphebetize them...
        matches.sort()

        # find the longest one
        maxlength = -1
        for m in matches:
            if len(m) > maxlength:
                maxlength = len(m)

        # figure out how many to put on a terminal line...
        per_line = self.gettc('co') // (maxlength + 2)

        # floor this to make sure it does not give issues below
        if per_line <= 0:
            per_line = 1

        # draw the table.
        for idx, m in enumerate(matches):
            extra = '  '
            if (idx % per_line) == per_line-1:
                extra = '\n'
            self.out_stream.write("{0:{width}}{1}".format(m, extra, width=maxlength))
        self.out_stream.write('\n')

    def show_history(self, args=None):
        # collect the current valid range
        first_ev = self.history(self.H_FIRST)
        last_ev = self.history(self.H_LAST)

        # we'll always finish here...
        finish = first_ev[0]

        # start?  assume "the beginning"
        idx = last_ev[0]

        # check the arg to see if it is a count of how many to display
        if args is not None and args.isnumeric():
            cnt = int(args)
            if cnt < first_ev[0]-last_ev[0]:
                idx = finish - cnt + 1

        # iterate through the list 'backwards' so the newest
        #   cmds are at the bottom
        while idx <= finish:
            try:
                ev = self.history(self.H_PREV_EVENT, idx)
                print("{0:3d}  {1}".format(ev[0], ev[1].rstrip()))
            except ValueError:
                pass    # probably should handle this better
            finally:
                idx += 1

    def _run_command(self, cmd):
        '''Is called from the C code upon completion of a line. Check
           for the existance of a "custom" command to implement'''
        # bail out immediately if no key
        if not (cmd.startswith("#!") or cmd.startswith(":")):
            return cmd

        # ok, it is one of the custom items

        # trim it
        cmd = cmd.replace('#!', '', 1).replace(':', '', 1).rstrip()

        # split it into a base-cmd + args
        parts = cmd.split(maxsplit=1)
        base_cmd = parts[0]
        args = ''
        if len(parts) > 1:
            args = parts[1]
        
        # command decode...
        if base_cmd == 'history':
            self.show_history(args)
            return None

        # a short-hand history cmd?
        if base_cmd.isnumeric():
            idx = int(base_cmd)
            #print("CMD: {:d}".format(idx))

            # get the valid range
            first_ev = self.history(self.H_FIRST)
            last_ev = self.history(self.H_LAST)

            # make sure the requested history item is possible
            if first_ev[0] >= idx >= last_ev[0]:

                # look up the historic command by number
                ev = self.history(self.H_PREV_EVENT, idx)
                if ev is None:
                    return None

                # extract the cmd and return it.
                return ev[1]

            # improper index
            print("Invalid history id: {:d}. Range is {:d} -> {:d}".format(idx, first_ev[0], last_ev[0]))
        
        # hmm. if we get here, it is an unknown infra cmd
        #   Error?  Certainly mark that it is consumed
        print("Invalid line-editor command.")
        return None

if __name__ == '__main__':
    import lineeditor
    eline = editline(sys.stdin, sys.stdout, sys.stderr)
    lineEd = lineeditor.Completer(subeditor=eline)
    eline.prompt = 'Cmd> '
    #eline.rl_completer = lineEd.rl_completer
    eline.completer = lineEd.completer
    eline.readline()

