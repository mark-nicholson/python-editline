#
#  tester file
#

import readline
import rlcompleter
readline.parse_and_bind("tab: complete")

#import editline
from   editline.elcompleter import Completer
from   editline.editline    import EditLine
from   editline.editline    import HistEdit

el = EditLine('orange')

ec = Completer()
#el.completer(ec.complete)

#
#  Try a fully custom prompt routine
#
def custom_prompt():
    return "CEL0>"

class Tomato():

    def __init__(self):
        self.my_str = 'Tomato> '

    def prompt(self):
        return self.my_str

# example:
el.prompt(custom_prompt)
# el.gets() will prompt with "CEL0>"

fruit = Tomato()
el.prompt(fruit.prompt)
# el.gets() will prompt Tomato>

fruit.my_str = "Orange# "
# el.gets() should prompt with "Orange# "

class SimpleCompleter():
    def __init__(self):
        self.matches = []
        self.items = [
            'Apple',
            'Banana',
            'Pear',
            'Peach',
            'Plum',
            'Orange']

    def complete(self, el, completion_char):
        #print("SimpleCompleter::complete( text=" + str(el) + "  state=%d" % completion_char)
        lineinfo = el.line()
        #print("Buffer: " + lineinfo.buffer)
        text = lineinfo.buffer[:lineinfo.cursor]
        #print("Text: " + text)
        self.matches = []
        for i in self.items:
            #print("    i = " + i)
            if i.startswith(text):
                self.matches.append(i)
        #print("Found: " + str(self.matches))

        if len(self.matches) > 1:
            print()
            print(self.matches)
            return HistEdit.CC_REDISPLAY
        elif len(self.matches) == 1:
            el.insertstr( self.matches[0][lineinfo.cursor:])
            return HistEdit.CC_REFRESH
        else:
            return HistEdit.CC_ERROR


sc = SimpleCompleter()
el.completer(sc.complete)
