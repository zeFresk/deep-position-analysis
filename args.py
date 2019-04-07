import argparse
import os.path
import sys

from multipv import MultiPV

###########################################
############ Arguments parsing ############
###########################################

def make_parser():
    """Create the default parser and setup args configuration."""

    parser = argparse.ArgumentParser(description="Generate pgn of possible variations from position.")

    parser.add_argument("fen_files", metavar='F', type=str, nargs='+', help="fen file to generate variation from")
    parser.add_argument("-p", "--engine", dest="engine_path", action="store", type=str, required=True, help="path to engine")
    parser.add_argument("--no-cache", dest="use_cache", action="store_const", const=False, default=True, help="use cache (increase I/O)")
    parser.add_argument("-c", "--config", dest="engine_config", action="store", type=str, default="<autodiscover>", help="path to engine configuration")
    parser.add_argument("--pv", dest="pv", action="store", type=str, default="2", help="number of best moves to explore per node (MultiPV expression)")
    parser.add_argument("--depth", dest="depth", action="store", type=int, default=2, help="number of plies to explore")
    parser.add_argument("--nodes", dest="nodes", action="store", type=int, default=-1, help="nodes to explore at each step before returning best move")
    parser.add_argument("--time", dest="sec", action="store", type=int, default=-1, help="time in seconds passed at each step before returning best move")
    parser.add_argument("--threshold", dest="threshold", action="store", type=int, default=25600, help="stop exploring further if the score (in centipawn) is above threshold.")
    parser.add_argument("--tree", dest="tree_exp", action="store_const", const=True, default=False, help="export final tree directly")
    parser.add_argument("--appending", dest="appending", action="store_const", const=True, default=False, help="append possible continuation to end nodes.") # carefull, inverted
    
    return parser

def parse_pv(pv_str, depth):
    """Parse a PV string to returns PV object."""
    try:
        return MultiPV(pv_str, depth)
    except:
        return None

def check_args(args): # Needed in next function
    """Make sure all needed arguments are set correctly, else exit."""
    if not os.path.isfile(args.engine_path):
        sys.stderr.write("!!Error: %s engine doesn't exists !\n"%(args.engine_path))
        sys.exit(-1)

    if args.nodes < 0 and args.sec < 0: #no stopping condition
        sys.stderr.write("!!Error: No stopping conditions, please set --nodes or --time !\n")
        sys.exit(-1)

    if args.nodes < 0: args.nodes = None
    if args.sec < 0: args.sec = None

    args.pv = parse_pv(args.pv, args.depth)
    if args.pv == None: # Error when parsing PV
        sys.stderr.write("!!Error: Incorrect PV : %s!\n"%(args.pv))
        sys.exit(-1)


    return args

def get_args():
    """Parse all args given to this script. Exit on error."""
    parser = make_parser()

    args = parser.parse_args()
    args = check_args(args)

    return args