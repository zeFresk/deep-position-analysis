# simple generator move tree from a fen using lc0

import argparse
import chess
import chess.pgn
import chess.uci
import sys
import time

def explore_rec(board, engine, pv, deepness, nodes):
    """
        Explore the current pgn position 'deepness' move deep using engine

        pgn : chess.Board() with an already setup board
        engine : chess.uci already loaded engine
        pv : we will explore top-'pv' moves
        deepness : deepness of final tree
        nodes : integer representing max nodes to explore per move

        Returns tree of moves and associated eval
           
        Warning : total nodes computed ~ (pv**deepness) * nodes !! Exponential growth !!
    """
    if deepness == 0:
        return None

    # Creating handler for multi-PV
    info_handler = chess.uci.InfoHandler()
    engine.info_handlers.append(info_handler)

     # Setting-up position for engine
    current_board = board
    engine.position(current_board)

    # Starting search
    print(">>> Analysing variation : [%s]..."%(current_board.fen()))
    cmd = engine.go(nodes=nodes, async_callback=True)
    sys.stdout.write(">>> 0% : ##\r")

    while not cmd.done(): #until search is finished
        with info_handler:
            if "nodes" in info_handler.info:
                sys.stdout.write(">>> %d%% : %s\r"%(int((info_handler.info["nodes"]/nodes) * 100),  chess.Board.san(current_board, info_handler.info["pv"][1][0])))

        time.sleep(0.250)

    # finshed
    sys.stdout.write("\r>>> 100%% : %s\n"%(chess.Board.san(current_board, info_handler.info["pv"][1][0])))

    # get all moves in an array
    moves = []
    for i in range(1, pv + 1):
        moves += [(info_handler.info["pv"][i][0], info_handler.info["score"][i].cp/100)]

    print(moves)

    if deepness == 1:
        return moves

    ret = []
    for mo, cp in moves: # explore new moves
        new_board = current_board
        new_board.push(mo)
        ret += [[[mo, cp], explore_rec(new_board, engine, pv, deepness-1, nodes)]]
    
    return ret

def loadOptions(engine):
    """Returns a dictionnary containing all engine options at their default value"""
    Options = engine.options
    ret = dict()
    
    for e in Options:
        ret[Options[e].name] = Options[e].default

    return ret

def append_variations(tree, pgn):
    """Append all variation from tree in pgn"""

    if tree == None:
        return
  
    for (move, cp), subtree in tree:
        node = pgn.add_variation(move, str(cp))
        append_variations(subtree, node)



def main():
    print("Parsing args...")
    # args parsing
    parser = argparse.ArgumentParser(description="Generate pgn of possible variations from position.")
    parser.add_argument("fen_files", metavar='F', type=str, nargs='+', help="fen file to generate variation from")
    parser.add_argument("--pv", dest="pv", action="store", type=int, default=2, help="number of best moves to explore per node")
    parser.add_argument("--deep", dest="deep", action="store", type=int, default=2, help="number of ply to explore")
    parser.add_argument("--nodes", dest="nodes", action="store", type=int, default=50000, help="node used to explore each node in seconds")

    args = parser.parse_args()

    #engine setup
    print("Setting-up engine")

    engine = chess.uci.popen_engine("E:/Programs/Arena/Engines/Lc0-v19/lc0.exe")
    engine.uci()
    #OptionMap({'Threads': Option(name='Threads', type='spin', default=2, min=1, max=128, var=[]), 
    #'NNCacheSize': Option(name='NNCacheSize', type='spin', default=200000, min=0, max=999999999, var=[]), 
    #'SyzygyPath': Option(name='SyzygyPath', type='string', default='', min=None, max=None, var=[]), 
    #'RamLimitMb': Option(name='RamLimitMb', type='spin', default=0, min=0, max=100000000, var=[]), 
    #'WeightsFile': Option(name='WeightsFile', type='string', default='<autodiscover>', min=None, max=None, var=[]), 
    #'Backend': Option(name='Backend', type='combo', default='cudnn', min=None, max=None, var=['cudnn', 'cudnn-fp16', 'check', 'random', 'multiplexing']), 
    #'CacheHistoryLength': Option(name='CacheHistoryLength', type='spin', default=0, min=0, max=7, var=[]), 
    #'MultiPV': Option(name='MultiPV', type='spin', default=1, min=1, max=500, var=[]), 
    #'HistoryFill': Option(name='HistoryFill', type='combo', default='fen_only', min=None, max=None, var=['no', 'fen_only', 'always']), 
    #'ConfigFile': Option(name='ConfigFile', type='string', default='lc0.config', min=None, max=None, var=[]), 
   
    opt = loadOptions(engine)

    opt["Threads"] = 2
    opt["NNCacheSize"] = 200000 * 10 # default *10
    opt["SyzygyPath"] = "E:/Programs/Arena/TB/syzygy"
    #opt["RamLimitMb"] = 2**32
    opt["WeightsFile"] = "E:/Programs/Arena/Engines/Lc0-v19/weights_11250.gz"
    opt["CacheHistoryLength"] = 2
    opt["MultiPV"] = args.pv
    opt["HistoryFill"] = "always"

    engine.setoption(opt)



    for filename in args.fen_files:
        file = open(filename)
        for (i, position_str) in enumerate(file): #iterate through lines
            print("Exploring [%s]..."%(position_str))

            board = chess.Board(position_str) # We load board

            # We generate variations tree
            tree = explore_rec(board, engine, args.pv, args.deep, args.nodes)
            print(tree)

            # We create pgn to export
            pos_pgn = chess.pgn.Game()
            pos_pgn.headers["Event"] = "Deep analysis of %s"%(position_str)
            pos_pgn.setup(board)

            # We append the tree
            #append_variations(tree, pos_pgn)

            # We save the pgn
            print(pos_pgn, file=open("%s_%d.pgn"%(filename, i), "w"), end="\n\n")
            
main()
