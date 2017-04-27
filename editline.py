
import sys
import os
import _editline

class editline(_editline.EditLine):

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

    def parse_and_bind(self, cmd):
        """Create the translation between "readline" and "bind" """
        key,routine = cmd.split(':')

        keymap = {
            'tab': ['^I'],
        }
        
    def _completer(self, text):

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
            #self.redisplay()
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

    def display_matches(self, matches):
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

        # draw the table.
        for idx,m in enumerate(matches):
            extra = '  '
            if (idx % per_line) == per_line-1:
                extra = '\n'
            self.out_stream.write("{0:{width}}{1}".format(m, extra, width=maxlength))
        self.out_stream.write('\n')


if __name__ == '__main__':
    import lineeditor
    foo = editline(sys.stdin, sys.stdout, sys.stderr)
    lec = lineeditor.Completer(editor_support=foo)
    foo.prompt = 'Cmd> '
    #foo.rl_completer = lec.stateful_complete
    foo.completer = lec.direct_complete
    foo.readline()

