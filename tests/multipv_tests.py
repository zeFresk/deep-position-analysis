###########################################
############ Dynamic PV  tests ############
###########################################

import unittest
import chess
from multipv import *

class Basic_PV(unittest.TestCase):

    def setUp(self):
        self.p2 = MultiPV("2",8)

    def test_pv_per_move_WHITE(self):
        turn = chess.WHITE
        for i in range(8,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), 2)
            turn = not turn

    def test_pv_per_move_BLACK(self):
        turn = chess.BLACK
        for i in range(8,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), 2)
            turn = not turn

    def test_total_nodes_WHITE(self):
        turn = chess.WHITE
        for i in range(8,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), (2**i -1))
            turn = not turn

    def test_total_nodes_BLACK(self):
        turn = chess.BLACK
        for i in range(8,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), (2**i -1))
            turn = not turn

class Complex_PV_Compile(unittest.TestCase):
    def test_Base(self):
        p = MultiPV("1",20)
    def test_Complex_Full(self):
        p = MultiPV("3-1/1m",20)
    def test_Complex_NoM(self):
        p = MultiPV("3-1/1",20)
    def test_Complex_NoLastD(self):
        p = MultiPV("3-1/m",20)
    def test_Complex_NoLastD_NoM(self):
        p = MultiPV("3-1",20)
    def test_Complex_Big_Plus(self):
        p = MultiPV("42+12/m",4)
    def test_Complex_Big_Minus(self):
        p = MultiPV("42-73/m",4)
    def test_composed_Base_Upper(self):
        p = MultiPV("3W1B", 20)
    def test_composed_Base_Lower(self):
        p = MultiPV("3w1b", 20)
    def test_composed_Base_Mixed(self):
        p = MultiPV("3w1B", 20)
    def test_composed_Complex_Upper(self):
        p = MultiPV("5-2/1MW3+1/2MB", 20)
    def test_composed_Complex_Lower(self):
        p = MultiPV("5-2/1mw3+1/2mb", 20)
    def test_composed_Complex_Mixed(self):
        p = MultiPV("5-2/1mW3+1/2Mb", 20)


class Singleton_Minus_PV(unittest.TestCase):

    def setUp(self):
        self.p2 = MultiPV("3-1/1m",4)
        self.moves = {4:3,3:3,2:2,1:2}
        self.total = {4:31,3:10,2:3,1:1}

    def test_pv_per_move_WHITE(self):
        turn = chess.WHITE
        for i in range(4,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), self.moves[i])
            turn = not turn

    def test_pv_per_move_BLACK(self):
        turn = chess.BLACK
        for i in range(4,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), self.moves[i])
            turn = not turn

    def test_total_nodes_WHITE(self):
        turn = chess.WHITE
        for i in range(4,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), self.total[i])
            turn = not turn

    def test_total_nodes_BLACK(self):
        turn = chess.BLACK
        for i in range(4,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), self.total[i])
            turn = not turn

    def test_no_zeros(self):
        p = MultiPV("3-1/1m", 20)
        for i in range(20, 0, -1):
            self.assertGreater(p.get_pvs(chess.WHITE, i), 0)

class Singleton_Plus_PV(unittest.TestCase):

    def setUp(self):
        self.p2 = MultiPV("2+1/1m",4)
        self.moves = {4:2,3:2,2:3,1:3}
        self.total = {4:19,3:9,2:4,1:1}

    def test_pv_per_move_WHITE(self):
        turn = chess.WHITE
        for i in range(4,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), self.moves[i])
            turn = not turn

    def test_pv_per_move_BLACK(self):
        turn = chess.BLACK
        for i in range(4,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), self.moves[i])
            turn = not turn

    def test_total_nodes_WHITE(self):
        turn = chess.WHITE
        for i in range(4,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), self.total[i])
            turn = not turn

    def test_total_nodes_BLACK(self):
        turn = chess.BLACK
        for i in range(4,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), self.total[i])
            turn = not turn

class Basic_Composed_PV(unittest.TestCase):

    def setUp(self):
        self.p2 = MultiPV("3W2b",4)
        self.movesW = {4:3,3:2,2:3,1:2}
        self.totalW = {4:28,3:9,2:4,1:1}
        self.movesB = {4:2,3:3,2:2,1:3}
        self.totalB = {4:21,3:10,2:3,1:1}

    def test_pv_per_move_WHITE(self):
        turn = chess.WHITE
        for i in range(4,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), self.movesW[i])
            turn = not turn

    def test_pv_per_move_BLACK(self):
        turn = chess.BLACK
        for i in range(4,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), self.movesB[i])
            turn = not turn

    def test_total_nodes_WHITE(self):
        turn = chess.WHITE
        for i in range(4,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), self.totalW[i])
            turn = not turn

    def test_total_nodes_BLACK(self):
        turn = chess.BLACK
        for i in range(4,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), self.totalB[i])
            turn = not turn

class Complex_Composed_PV(unittest.TestCase):

    def setUp(self):
        self.p2 = MultiPV("3-1W2+1b",5)
        self.movesW = {5:3,4:2,3:2,2:3,1:1}
        self.totalW = {5:58,4:19,3:9,2:4,1:1}
        self.movesB = {5:2,4:3,3:3,2:2,1:4}
        self.totalB = {5:63,4:31,3:10,2:3,1:1}

    def test_pv_per_move_WHITE(self):
        turn = chess.WHITE
        for i in range(5,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), self.movesW[i])
            turn = not turn

    def test_pv_per_move_BLACK(self):
        turn = chess.BLACK
        for i in range(5,0,-1):
            self.assertEqual(self.p2.get_pvs(turn,i), self.movesB[i])
            turn = not turn

    def test_total_nodes_WHITE(self):
        turn = chess.WHITE
        for i in range(5,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), self.totalW[i])
            turn = not turn

    def test_total_nodes_BLACK(self):
        turn = chess.BLACK
        for i in range(5,0,-1):
            self.assertEqual(self.p2.max_nodes(turn, i), self.totalB[i])
            turn = not turn

if __name__ == '__main__':
    unittest.main()
