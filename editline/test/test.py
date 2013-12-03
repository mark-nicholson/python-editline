#
#  tester file
#

import editline
from   elcompleter import Completer

el = editline.EditLine('orange')

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

