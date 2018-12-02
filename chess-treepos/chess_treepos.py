# simple generator move tree from a fen using lc0

import argparse

import chess
import chess.pgn
import chess.uci

import sys
import time
import os.path


def explore_rec(board, engine, pv, depth, nodes):
    """
        Explore the current pgn position 'depth' plys deep using engine

        pgn : chess.Board() with an already setup board
        engine : chess.uci already loaded engine
        pv : we will explore top-'pv' moves
        depth : depth of final tree
        nodes : integer representing max nodes to explore per move

        Returns tree of moves and associated eval
           
        Warning : total nodes computed ~ (pv**depth) * nodes !! Exponential growth !!
    """
    if depth == 0:
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
        time.sleep(0.100)
        with info_handler:
            if "nodes" in info_handler.info and "pv" in info_handler.info:
                sys.stdout.write(">>> %d%% : %s\r"%(int((info_handler.info["nodes"]/nodes) * 100),  chess.Board.san(current_board, info_handler.info["pv"][1][0])))


    # finshed
    sys.stdout.write("\r>>> 100%% : %s\n"%(chess.Board.san(current_board, info_handler.info["pv"][1][0])))

    # get all moves in an array
    moves = []
    for i in range(1, pv + 1):
        moves += [(info_handler.info["pv"][i][0], info_handler.info["score"][i].cp/100)]

    if depth == 1:
        return moves

    ret = []
    for (mo, cp) in moves: # explore new moves
        new_board = chess.Board(current_board.fen())
        new_board.push(mo)
        ret += [[(mo, cp), explore_rec(new_board, engine, pv, depth-1, nodes)]]
    
    return ret

def write_config(opt, file):
    """Export options dictionnary to config file."""
    if "multiPV" in opt:
         del opt["MultiPV"] # the value will be set by us later

    for key, value in opt.items():
        file.write("%s = %s\n"%(str(key), str(value)))

def update_options_from_config(opt, file):
    """Read a config and update dictionnary opt"""
    data = file.readlines()
    for line in data:
        key, val = line.split('=')
        opt[key.strip()] = val.strip() #remove whitespace

    return opt

def default_options(engine):
    """Returns a dictionnary containing all engine options at their default value"""
    Options = engine.options
    ret = dict()
    
    for e in Options:
        ret[Options[e].name] = Options[e].default

    return ret

def load_options(engine, config):
    """ Load engine uci options from config, if no config exists will create one."""
    if config == "<autodiscover>": #no config provided
        engine_name = engine.name.split()[0] # first string in name
        config = engine_name + ".cfg"

        if not os.path.isfile(config): # no existing config file
            print("\n!Warning: No config file for %s detected, creating one. Default values used.\n"%(engine_name))
            f = open(config, "w")

            opt = default_options(engine)
            write_config(opt, f) # exporting config to file

            return opt

    if os.path.isfile(config): # custom or default config exists
        opt = default_options(engine)

        f = open(config, "r")
        update_options_from_config(opt, f)
        return opt

    else: #no config found
        sys.stderr.write("!!Error: config %s doesn't exists ! Exiting...\n")
        sys.exit(-2)

def append_variations_rec(tree, pgn, depth):
    if depth < 0:
        return
    move = 0
    cp = 0
    if depth == 0:
        move, cp = tree
    else:
        move, cp = tree[0]
    node = pgn.add_variation(move, str(cp))
    for i in range(1, len(tree)):
        append_variations(tree[i], node, depth)

def append_variations(tree, pgn, depth):
    """Append all variation from tree in pgn"""
    if depth == 0:
        return
    for i in range(len(tree)): # for each PV
        append_variations_rec(tree[i], pgn, depth - 1)


def main():
    print("Parsing args...")
    # args parsing
    parser = argparse.ArgumentParser(description="Generate pgn of possible variations from position.")
    parser.add_argument("fen_files", metavar='F', type=str, nargs='+', help="fen file to generate variation from")
    parser.add_argument("-p", "--engine", dest="engine_path", action="store", type=str, required=True, help="path to engine")
    parser.add_argument("-c", "--config", dest="engine_config", action="store", type=str, default="<autodiscover>", help="path to engine configuration")
    parser.add_argument("--pv", dest="pv", action="store", type=int, default=2, help="number of best moves to explore per node")
    parser.add_argument("--depth", dest="depth", action="store", type=int, default=2, help="number of plies to explore")
    parser.add_argument("--nodes", dest="nodes", action="store", type=int, default=50000, help="node used to explore each node in seconds")

    args = parser.parse_args()

    #engine setup
    print("Setting-up engine")

    if not os.path.isfile(args.engine_path):
        sys.stderr.write("!!Error: %s engine doesn't exists ! Exiting...\n"%(args.engine_path))
        sys.exit(-1)

    engine_path = args.engine_path

    engine = chess.uci.popen_engine(engine_path)
    engine.uci()
   
    opt = load_options(engine, args.engine_config)

    #opt["Threads"] = 3
    #opt["NNCacheSize"] = 200000 * 10 # default *10
    #opt["SyzygyPath"] = "E:/Programs/Arena/TB/syzygy"
    ##opt["RamLimitMb"] = 2**32
    #opt["WeightsFile"] = "E:/Programs/Arena/Engines/Lc0-v19/weights_11250.gz"
    #opt["CacheHistoryLength"] = 2
    opt["MultiPV"] = args.pv

    engine.setoption(opt)



    for filename in args.fen_files:
        file = open(filename)
        for (i, position_str) in enumerate(file): #iterate through lines
            print("Exploring [%s]..."%(position_str))

            board = chess.Board(position_str) # We load board

            # We generate variations tree
            tree = explore_rec(board, engine, args.pv, args.depth, args.nodes)

            # We create pgn to export
            pos_pgn = chess.pgn.Game()
            pos_pgn.headers["Event"] = "DeA at %d nodes, %d ply-depth, of %s"%(args.nodes, args.depth, position_str)
            pos_pgn.setup(board)

            # We append the tree
            append_variations(tree, pos_pgn, args.depth)

            # We save the pgn
            index = filename.find(".")
            if index == -1:
                index = len(filename)
            print(pos_pgn, file=open("%s%d_%dn%dd.pgn"%(filename[0:index], i, args.nodes, args.depth), "w"), end="\n\n")
            
main()
