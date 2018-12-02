# simple generator move tree from a fen using lc0

import argparse

import chess
import chess.pgn
import chess.uci

import sys
import time
import os.path
import io

import re

time_st = 0

def format_nodes(n):
    """Select appropriate form for big values."""
    if n < 10**3: #less than 3 digits
        return "%d"%(n)
    elif n < 10**6: #less than 6 digits => Knodes
        return "{:1.1f}K".format(n/1000)
    elif n < 10**9: #less than 9 digits => Mnodes
        return "{:1.1f}M".format(n/10**6)
    elif n < 10**12: #less than 9 digits => Gnodes
        return "{:1.1f}G".format(n/10**9)
    else: #more than 10^12
        return "{:1.1f}T".format(n/10**12)


def explore_rec(board, engine, pv, depth, nodes, msec = None, tot = None):
    """
        Explore the current pgn position 'depth' plys deep using engine

        pgn : chess.Board() with an already setup board
        engine : chess.uci already loaded engine
        pv : we will explore top-'pv' moves
        depth : depth of final tree
        nodes : integer representing max nodes to explore per move
        msec : time in milliseconds before stopping exploration

        Returns tree of moves and associated eval
           
        Warning : total nodes computed ~ (pv**depth) * nodes !! Exponential growth !!
    """
    global pos_index
    if tot == None: #first turn
        tot = (pv**depth)-1
        pos_index = 0

    if depth == 0:
        return None

    pos_index += 1

    # Creating handler for multi-PV
    info_handler = chess.uci.InfoHandler()
    engine.info_handlers.append(info_handler)

     # Setting-up position for engine
    current_board = board
    engine.position(current_board)

    # Starting search
    elapsed_time = time.clock() - time_st

    if elapsed_time == 0: #avoid divising by 0
        elapsed_time = 1

    sys.stdout.buffer.close = lambda: None # atrocity but needed
    out = io.TextIOWrapper(sys.stdout.buffer, line_buffering = False)

    pos_per_s = pos_index/elapsed_time # average positions per second
    remaining_time_s = (tot-(pos_index-1)) / pos_per_s
    print(">Analysing variation %d of %d, estimated time remaining : %dh %dm..."%(pos_index, tot, remaining_time_s // (60*60), (remaining_time_s // 60) %60), flush=True)
    cmd = engine.go(nodes=nodes, movetime=msec, async_callback=True)
    out.write(">> 0% : ###")

    while not cmd.done(): #until search is finished
        time.sleep(0.100)
        with info_handler:
            if "nodes" in info_handler.info and "pv" in info_handler.info and "nps" in info_handler.info:
                prct = 0
                if nodes != None: #we use nodes as stop
                    prct = int(info_handler.info["nodes"])/nodes
                else: # we use time as stop
                    prct = int(info_handler.info["time"])/msec

                out.write("\r" + " "*30) # cleaning line
                out.write("\r>> {:.1%} @ {:s}nodes/s : {:s}".format(prct, format_nodes(int(info_handler.info["nps"])), chess.Board.san(current_board, info_handler.info["pv"][1][0])))
                out.flush()


    # finshed
    out.write("\r" + " "*30) # cleaning line
    out.write("\r>> 100%% @ {:s}nodes/s : {:s}\n\n".format(format_nodes(int(info_handler.info["nps"])), chess.Board.san(current_board, info_handler.info["pv"][1][0])))
    out.flush()

    # get all moves in an array
    moves = []
    for i in range(1, pv + 1):
        with info_handler:
            score = 0 if info_handler.info["score"][i].cp == None else info_handler.info["score"][i].cp # to avoid null cp at few nodes
            moves += [(info_handler.info["pv"][i][0], score/100)]

    if depth == 1:
        return moves

    ret = []
    for (mo, cp) in moves: # explore new moves
        new_board = chess.Board(current_board.fen())
        new_board.push(mo)
        ret += [[(mo, cp), explore_rec(new_board, engine, pv, depth-1, nodes, msec, tot)]]
    
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
    parser.add_argument("--tree", dest="tree_exp", action="store_const", const=True, default=False, help="export final tree directly")
    parser.add_argument("--pv", dest="pv", action="store", type=int, default=2, help="number of best moves to explore per node")
    parser.add_argument("--depth", dest="depth", action="store", type=int, default=2, help="number of plies to explore")
    parser.add_argument("--nodes", dest="nodes", action="store", type=int, default=-1, help="nodes to explore at each step before returning best move")
    parser.add_argument("--time", dest="sec", action="store", type=int, default=-1, help="time in seconds passed at each step before returning best move")

    args = parser.parse_args()

    #engine setup
    print("Setting-up engine")

    if not os.path.isfile(args.engine_path):
        sys.stderr.write("!!Error: %s engine doesn't exists ! Exiting...\n"%(args.engine_path))
        sys.exit(-1)

    if args.nodes < 0 and args.sec < 0: #no stopping condition
        sys.stderr.write("!!Error: No stopping conditions, please set --nodes or --time ! Exiting...\n"%(args.engine_path))
        sys.exit(-1)

    if args.nodes < 0: args.nodes = None
    if args.sec < 0: args.sec = None

    engine_path = args.engine_path

    engine = chess.uci.popen_engine(engine_path)
    engine.uci()
   
    opt = load_options(engine, args.engine_config)

    opt["MultiPV"] = args.pv

    engine.setoption(opt)



    for filename in args.fen_files:
        file = open(filename)
        file = file.readlines()
        for (i, position_str) in enumerate(file): #iterate through lines
            print("\nExploring fen %d of %d : [%s]...\n"%(i+1, len(file), position_str.strip()))

            board = chess.Board(position_str) # We load board

            time_st = time.time()

            # We generate variations tree
            msec = None
            if args.sec != None: msec = args.sec*1000
            tree = explore_rec(board, engine, args.pv, args.depth, args.nodes, msec)

            #formatting
            index = filename.find(".")
            if index == -1:
                index = len(filename)

            stopping_fmt = (str(args.nodes) +"n") if (args.nodes != None) else (str(args.sec)+"s")
            full_fmt = "%s%d_%s%dd"%(filename[0:index], i, stopping_fmt, args.depth)
            
            if not args.tree_exp: #export as pgn
                # We create pgn to export
                pos_pgn = chess.pgn.Game()
                stopping = args.nodes if (args.nodes != None) else args.sec
                pos_pgn.headers["Event"] = "DeA using %s at %s per move, %d ply-depth, of %s"%(engine.name, stopping, args.depth, position_str)
                pos_pgn.headers["White"] = engine.name
                pos_pgn.headers["Black"] = engine.name
                pos_pgn.setup(board)

                # We append the tree
                append_variations(tree, pos_pgn, args.depth)

                elapsed = time.time() - time_st # in seconds
                print("Completed position analysis %d of %d from %s in %d hours %d minutes %d seconds.\nSaving result.\n"%(i+1, len(file), filename, elapsed // (60*60), (elapsed // 60)%60, elapsed % 60))

                # We save the pgn
                print(pos_pgn, file=open("%s.pgn"%(full_fmt), "w"), end="\n\n")

            else: #export raw tree
                 # We save the tree
                print(tree, file=open("%s.tree"%(full_fmt), "w"), end="\n")

                #delete artefacts
                f = open("%s.tree"%(full_fmt), "r")
                lines = f.readlines()
                f.close()
                out = open("%s.tree"%(full_fmt), "w")

                reg = r"Move\.from_uci\(\'(\w+)\'\)"
                for l in lines:
                    l = re.sub(reg, r"\1", l)
                    l = l.replace("(", "{")
                    l = l.replace(")", "}")
                    l = l.replace("[", "{")
                    l = l.replace("]", "}")
                    out.write(l)

main()
