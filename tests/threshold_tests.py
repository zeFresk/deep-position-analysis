###########################################
############ Threshold  tests #############
###########################################

import unittest
from threshold import *

class Empty_Threshold(unittest.TestCase):
    def setUp(self):
        self.th = Threshold("")
    def test_full_range(self):
        for i in range(-128,129):
            self.assertFalse(self.th.above_threshold(i))

class Basic_Threshold(unittest.TestCase):
    def setUp(self):
        self.th = Threshold("5")
        self.set = {0.0:False, 4.9:False, -4.9:False, 5.1: True, -5.1: True}

    def test_full_range(self):
        for k, v in self.set.items():
            self.assertEqual(self.th.above_threshold(k), v)

    def test_extremes(self):
        self.assertTrue(self.th.above_threshold(-128))
        self.assertTrue(self.th.above_threshold(128))

class Half_Threshold(unittest.TestCase):
    def setUp(self):
        self.thW = Threshold("5W")
        self.thB = Threshold("5B")

    def test_all_bv_thw(self):
        for i in range(-128,0,2):
            self.assertFalse(self.thW.above_threshold(i))

    def test_all_wv_thb(self):
        for i in range(0,128,2):
            self.assertFalse(self.thB.above_threshold(i))

    def test_wv(self):
        for i in [p/10 for p in range(0,50,1)]:
            self.assertFalse(self.thW.above_threshold(i))
        for i in [p/10 for p in range(51,1280,1)]:
            self.assertTrue(self.thW.above_threshold(i))

    def test_bv(self):
        for i in [p/10 for p in range(-50,0,1)]:
            self.assertFalse(self.thB.above_threshold(i))
        for i in [p/10 for p in range(-1280,-51,1)]:
            self.assertTrue(self.thB.above_threshold(i))

class Complex_Threshold(unittest.TestCase):
    def setUp(self):
        self.th = Threshold("1.00W5.00B")

    def test_all_wv(self):
        for i in [p/10 for p in range(0,10,1)]:
            self.assertFalse(self.th.above_threshold(i))
        for i in [p/10 for p in range(11,1280,1)]:
            self.assertTrue(self.th.above_threshold(i))

    def test_all_bv(self):
        for i in [p/10 for p in range(-50,0,1)]:
            self.assertFalse(self.th.above_threshold(i))
        for i in [p/10 for p in range(-1280,-51,1)]:
            self.assertTrue(self.th.above_threshold(i))



if __name__ == '__main__':
    unittest.main()
