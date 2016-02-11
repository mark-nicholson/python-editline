"""
Unit test infrastructure for the Editline interface.

Create an extensible test infrastructure to efficiently validate all of the APIs.
"""
import unittest
from test.support import run_unittest, import_module

# Skip tests if there is no readline module
editline = import_module('editline.editline')

class TestHistory (unittest.TestCase):

    def setUp(self):
        self.h = editline.History()

    def tearDown(self):
        self.h = None

    def testAppend(self):

        self.h.append("first")
        self.h.append("second")
        self.h.append("third")

        self.assertEqual( len(self.h), 3 )

    def testArrayAppend(self):
        self.h[4] = "FOURTH"
        self.h[5] = "FIFTH"
        self.h[6] = "SIXTH"
        
        self.assertEqual( len(self.h), 6 )

    def testSize(self):

        self.assertEqual( self.h.set_size(64), 0 )
        self.assertEqual( self.h.get_size(), 64 )
        
        self.assertEqual( self.h.set_size(16), 0 )
        self.assertEqual( self.h.get_size(), 16 )

        self.assertEqual( self.h.set_size(128), 0 )
        self.assertEqual( self.h.get_size(), 128 )
        

    # def testHistoryUpdates(self):
    #     readline.clear_history()

        # readline.add_history("first line")
        # readline.add_history("second line")

        # self.assertEqual(readline.get_history_item(0), None)
        # self.assertEqual(readline.get_history_item(1), "first line")
        # self.assertEqual(readline.get_history_item(2), "second line")

        # readline.replace_history_item(0, "replaced line")
        # self.assertEqual(readline.get_history_item(0), None)
        # self.assertEqual(readline.get_history_item(1), "replaced line")
        # self.assertEqual(readline.get_history_item(2), "second line")

        # self.assertEqual(readline.get_current_history_length(), 2)

        # readline.remove_history_item(0)
        # self.assertEqual(readline.get_history_item(0), None)
        # self.assertEqual(readline.get_history_item(1), "second line")

        # self.assertEqual(readline.get_current_history_length(), 1)


def test_main():
    run_unittest(TestHistory)

if __name__ == "__main__":
    test_main()
