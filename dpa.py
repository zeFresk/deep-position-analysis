# simple generator move tree from a fen using lc0

import argparse

import chess
import chess.pgn
import chess.uci

from operator import itemgetter
import sys
import time
import os.path
import io
import copy
import traceback

import re

def format_nodes(n, fmt="{:1.1f}"):
    """Select appropriate form for big values."""
    if n < 10**3: #less than 3 digits
        return "%d"%(n)
    elif n < 10**6: #less than 6 digits => Knodes
        return (fmt+"k").format(n/1000)
    elif n < 10**9: #less than 9 digits => Mnodes
        return (fmt+"m").format(n/10**6)
    elif n < 10**12: #less than 9 digits => Gnodes
        return (fmt+"g").format(n/10**9)
    else: #more than 10^12
        return (fmt+"t").format(n/10**12)

def fmt_mate(mate_score):
    """Format a mate value as a proper string."""
    if mate_score < 0: # mate in X for black
        return "-M{:d}".format(abs(mate_score))
    else: # mate in X for white
        return "+M{:d}".format(abs(mate_score))

def worst_case_treenodes(degree, depth):
    """Compute the total number of nodes in a tree of constant branching factor for the given depth"""
    return ((degree**(depth))-1)/(degree-1)

def elapsed_since(timestamp):
    """Returns elapsed time since a given timestamp in seconds.
    It will always returns at least one."""
    ret = time.perf_counter() - timestamp
    return ret if ret >= 1 else 1

class Explorator(object):
    def __init__(self):
        """Create an empty Explorator"""
        # Variables used to avoid copy (as if we copied the stack)
        self.engine = None
        self.pv = None
        self.nodes = None
        self.msec = None
        self.appending = None

        # Variables used globally
        self.crashed_once = None
        self.tot = None
        self.time_st = None
        self.info_handler = None
        self.pos_index = None
        self.out = None

    def explore(self, board, engine, pv, depth, nodes, msec = None, appending = True):
        """
            Explore the current pgn position 'depth' plys deep using engine

            pgn : chess.Board() with an already setup board
            engine : chess.uci already loaded engine
            pv : we will explore top-'pv' moves
            depth : depth of final tree
            nodes : integer representing max nodes to explore per move
            msec : time in milliseconds before stopping exploration

            Returns tree of moves and associated eval
           
            Warning : total nodes computed ~ ((pv**(depth-1)-1)/(pv-1) * nodes !! Exponential growth !!
        """
        ##################
        # Stack optimization
        self.engine = engine
        self.pv = pv
        self.nodes = nodes
        self.msec = msec
        self.appending = appending
        ##################
        # Here are all the variables commons to all recursions
        self.crashed_once = False # Needed to not print too much errors in case of a crash
        self.tot = worst_case_treenodes(pv, depth) # total number of nodes in the final tree, worst case scenario.

        self.time_st = time.perf_counter() # We initialize starting time

        self.info_handler = chess.uci.InfoHandler() # We will communicate with the engine using this
        self.engine.info_handlers.append(self.info_handler) 

        self.pos_index = 0 # Number of variations already explored

        #sys.stdout.buffer.close = lambda: None # atrocity but needed
        self.out = io.TextIOWrapper(sys.stdout.buffer, line_buffering = False) # We create a common non-buffered output

        #################
        # We then need to call the main function
        return self._explore_rec(board, depth)


    def _explore_rec(self, board, depth): # less parameters so less copy
        """Main recursive function."""
        try:
            if depth == 0:
                return None

            self.pos_index += 1

            # Setting-up position for engine
            self.engine.position(board)
            # Start search
            cmd = self.engine.go(nodes=self.nodes, movetime=self.msec, async_callback=True)
            self.display_global_progress()

            while not cmd.done(): # until search is finished
                time.sleep(0.00001) # Sleep for 10 µs to not use full core
                self.display_position_progress(board)

            self.display_position_progress(board, end="\n\n") # Needed if we don't want the line to be blank in case it finished too fast

            # get all moves in an array
            moves = self.get_all_moves(depth) # We extract all moves available

            if depth == 1: #last nodes
                if self.appending: # We append all continuation to last node then
                    for i in range(len(moves)):
                        moves[i][0] = self.info_handler.info["pv"][i+1] # We add the full movelist to the node

                return moves

            ret = []
            for (mo, cp) in moves: # explore new moves
                new_board = copy.deepcopy(board) # We copy the current board

                if not new_board.is_legal(mo): # If the move is illegal (it can happen with Leela)
                    raise RuntimeError("Illegal move : {:s} in {:s}\n".format(new_board.san(mo), new_board.fen())) # We throw an exception

                new_board.push(mo)
                if not new_board.is_game_over(claim_draw=True): # If the game isn't drawn or won by a player we continue
                    ret += [[(mo, cp), self._explore_rec(new_board, depth-1)]]
                else:
                    tot -= worst_case_tree_nodes(self.pv, depth-1)*(self.pv - self.info_handler.info["multipv"]) # We need to update its value because less nodes need to be explored
                    ret += [[(mo, cp),[]]] #terminal node
    
            return ret
        except :
            if not self.crashed_once: # We only print the bug message if we are in the first recursive call
                print("\nCongratulations, you found a bug ! A bug report is generated in bug.log\nPlease help me correct it by linking the report to your message :)\n")
                self.crashed_once = True

            self.log_bug("bug.log", board, depth, sys.exc_info())
            raise # to unstack

    def log_bug(self, filename, board, depth, exc_tuple):
        """Log an exception which occured in a given board to a file."""
        exc_type, exc_value, exc_traceback = exc_tuple # get full exception with traceback
        fbug = open("bug.log", "a")
        exception_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)) # We format the exception before saving it

        fbug.write("bug in fen = [{:s}] with \"{:s}\", PV={:d} NODES={:d} DEPTH={:d}\n####\n{:s}\n\n".format(board.fen(), self.engine.name, self.pv, self.nodes, depth, exception_str))


    def get_all_moves(self, depth):
        """Returns all the first moves computed and update total number of nodes to explore if needed."""
        ret = []
        with self.info_handler: # We need to lock the handler
            if self.info_handler.info["multipv"] < self.pv: #less pv generated than requested, whatever the reason
                self.tot -= worst_case_treenodes(self.pv, depth-1)*(self.pv - self.info_handler.info["multipv"]) # We need to update its value because less nodes need to be explored
            for i in range(1, self.info_handler.info["multipv"]+1):
                ret += [[self.info_handler.info["pv"][i][0], self.get_pv_score(i)]]
        
        return ret

    def display_global_progress(self):
        """Display the global progress in analyzing all the possible variations along with estimated time needed."""
        elapsed_time = elapsed_since(self.time_st) # Getting elapsed time from start

        pos_per_s = self.pos_index/elapsed_time # average positions per second
        remaining_time_s = (self.tot-(self.pos_index-1)) / pos_per_s
        print(">Analysing variation %d of %d, estimated time remaining : %dh %dm..."%(self.pos_index, self.tot, remaining_time_s // (60*60), (remaining_time_s // 60) %60), flush=True)
        self.out.write(">> 0% : ###")

    def display_position_progress(self, current_board, end=""):
        """Display the progress analyzing the current position. Can take a lot of time since we need to lock a mutex."""
        with self.info_handler: # Waiting for the handler to be locked
            if "nodes" in self.info_handler.info and "pv" in self.info_handler.info and "nps" in self.info_handler.info and "score" in self.info_handler.info: # Make sure all values are set
                
                prct = 0
                if self.nodes != None: #we use nodes as stop
                    prct = int(self.info_handler.info["nodes"])/self.nodes
                else: # we use time as stop
                    prct = int(self.info_handler.info["time"])/self.msec

                if prct >= 1.00: # we can't exceed 100% !
                    prct = 1.00

                self.out.write("\r" + " "*40) # cleaning line
                self.out.write("\r>> {:.0%} @ {:s}nodes/s : {:s} ({:s}){:s}".format(prct, format_nodes(int(self.info_handler.info["nps"])), chess.Board.san(current_board, self.info_handler.info["pv"][1][0]), self.get_pv_score(1), end))
                self.out.flush()

    def get_pv_score(self, i):
        """Returns score associated to i-th PV formatted as a string. !!! WE SUPPOSE HANDLER IS LOCKED !!!"""
        if self.info_handler.info["score"][1].cp == None: # Mate or draw
            return fmt_mate(self.info_handler.info["score"][1].mate)
        else:
            return "{:+.2f}".format(self.info_handler.info["score"][1].cp/100.)


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

    node = None
    if depth == 0:
        moves, cp = tree
        try: #if multiple moves
            iter(moves)
            node = pgn.add_variation(moves[0], comment=str(cp))
            for i in range(1,len(moves)): #until last move
                node = node.add_variation(moves[i])
        except TypeError: #only one move
            node = pgn.add_variation(moves, comment=str(cp))

    else:
        move, cp = tree[0]
        node = pgn.add_variation(move, comment=str(cp))

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
    parser.add_argument("--nodes", dest="nodes", action="store", type=int, default=-1, help="nodes to explore at each step before returning best move")
    parser.add_argument("--time", dest="sec", action="store", type=int, default=-1, help="time in seconds passed at each step before returning best move")
    parser.add_argument("--tree", dest="tree_exp", action="store_const", const=True, default=False, help="export final tree directly")
    parser.add_argument("--no-appending", dest="appending", action="store_const", const=False, default=True, help="do not append possible continuation to end nodes.") # carefull, inverted

    args = parser.parse_args()

    #engine setup
    print("Setting-up engine")

    if not os.path.isfile(args.engine_path):
        sys.stderr.write("!!Error: %s engine doesn't exists ! Exiting...\n"%(args.engine_path))
        sys.exit(-1)

    if args.nodes < 0 and args.sec < 0: #no stopping condition
        sys.stderr.write("!!Error: No stopping conditions, please set --nodes or --time ! Exiting...\n")
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
        data = []
        if filename[-4:] == ".pgn": # pgn input detected we will skip through last position
            print("PGN input detected we will only analyze from last position(s) reached.")

            game = chess.pgn.read_game(file)
            while game != None: # there is still at least one game to parse
                board = game.board() # set up board to initial position

                for move in game.main_line(): # iterate through mainline
                    board.push(move)

                data += [board.fen()]
                game = chess.pgn.read_game(file) # try to 
        else: #standard .fen or .epd
            data = file.readlines()

        for (i, position_str) in enumerate(data): #iterate through lines
            print("\nExploring position %d of %d : [%s]...\n"%(i+1, len(data), position_str.strip()))

            board = chess.Board(position_str) # We load board

            global time_st 
            time_st = time.perf_counter()

            # We generate variations tree
            msec = None
            if args.sec != None: msec = args.sec*1000
            exp = Explorator()
            tree = exp.explore(board, engine, args.pv, args.depth, args.nodes, msec, args.appending)

            # finished : show message
            elapsed = time.perf_counter() - time_st # in seconds
            print("Completed position analysis %d of %d from %s in %d hours %d minutes %d seconds.\nSaving result.\n"%(i+1, len(data), filename, elapsed // (60*60), (elapsed // 60)%60, elapsed % 60))

            #formatting
            index = filename.find(".")
            if index == -1:
                index = len(filename)

            stopping_fmt = (format_nodes(args.nodes,"{:1.0f}") +"n") if (args.nodes != None) else (str(args.sec)+"s")
            full_fmt = "%s%d_%s%dv%dp"%(filename[0:index], i, stopping_fmt, args.pv, args.depth)
            
            if not args.tree_exp: #export as pgn
                game = None # will contains final game to export to file
                if filename[-4:] != ".pgn": # input was not a pgn
                    # We create new game to export
                    game = chess.pgn.Game()
                    stopping = (format_nodes(args.nodes,"{:1.0f}") +" nodes") if (args.nodes != None) else (str(args.sec)+" seconds")
                    game.headers["Event"] = "DeA using %s at %s per move, %d PV, %d ply-depth, of %s"%(engine.name, stopping, args.pv, args.depth, position_str)
                    game.headers["White"] = engine.name
                    game.headers["Black"] = engine.name           

                    game.setup(board)

                    # We append the tree
                    append_variations(tree, game, args.depth)

                else: # input was a pgn we need to append at the end of it
                    file_tmp = open(filename) # we reload pgn

                    game = chess.pgn.read_game(file_tmp)
                    for _ in range(i): # skip to i-th game in pgn
                        game = chess.pgn.read_game(file_tmp)

                    last_node = game.end() # iterate through last node from main variation
                    stopping = (format_nodes(args.nodes,"{:1.0f}") +" nodes") if (args.nodes != None) else (str(args.sec)+" seconds")
                    txt = "Deep analysis start after that node"
                    last_node.comment = txt if (last_node.comment == "") else (last_node.comment + " | %s"%(txt)) # if a comment already exists append analysis msg to it

                    # We append the tree at the end
                    append_variations(tree, last_node, args.depth)

                # We save the game as pgn
                print(game, file=open("%s.pgn"%(full_fmt), "w"), end="\n\n")

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