# (simple) generator move tree from a fen using lc0

import chess
import chess.pgn
import chess.uci

from operator import itemgetter
import sys
import time

import io
import copy
import traceback

import re

from args import * # Imports all argument parsing functions
from files import * # Imports all files and PGN related functions
from misc import * # Imports wide variety of usefull functions
from core import * # Imports Explorer class and core functions
from uci import * # Needed to communicate with the engine
from cache import *


###########################################
############### Entry point ###############
###########################################

async def main():
    # args parsing
    args = get_args()

    #engine setup
    print("Setting-up engine")
    engine_path = args.engine_path

    engine = chess.uci.popen_engine(engine_path)
    engine.uci()
   
    opt = load_options(engine, args.engine_config)
    opt["MultiPV"] = args.pv
    engine.setoption(opt)
    t = hash_opt(opt)

    # cache setup
    cache = None
    if args.use_cache:
        cache = Cache()
        await cache.load(20, ".cached.db", engine, opt)

    for filename in args.fen_files:
        fens = fens_from_file(filename)
        
        for (i, position_str) in enumerate(fens): #iterate through lines
            print("\nExploring position %d of %d : [%s]...\n"%(i+1, len(fens), position_str.strip()))
            board = chess.Board(position_str) # We load board

            time_st = time.perf_counter() # Setting up starting time to keep track
            msec = None if args.sec == None else args.sec*1000 # converting seconds to ms if needed
            
            # Explore current fen
            exp = Explorator()
            tree = await exp.explore(board, engine, cache, args.pv, args.depth, args.nodes, msec, args.threshold, args.appending)

            # finished : show message
            elapsed = time.perf_counter() - time_st # in seconds
            print("Completed position analysis %d of %d from %s in %d hours %d minutes %d seconds.\nSaving result.\n"%(i+1, len(fens), filename, elapsed // (60*60), (elapsed // 60)%60, elapsed % 60))

            output_filename = format_filename(filename, i, args) #retrieve output filename without extension
            
            if not args.tree_exp: #export as pgn
                game = None # will contains final game to export to file
                if not is_pgn(filename): # input was not a pgn
                    game = new_default_game(board, engine.name, args) # Create a gaame with the correct headers
                    append_variations(tree, game, args.depth) # Update the game with our computed tree

                else: # input was a pgn we need to append at the end of it
                    game = load_ith_from_pgn(filename, i)

                    last_node = game.end() # iterate through last node from main variation

                    txt = "Deep analysis start after that node"
                    last_node.comment = txt if (last_node.comment == "") else (last_node.comment + " | %s"%(txt)) # if a comment already exists append analysis msg to it

                    # We append the tree at the end
                    append_variations(tree, last_node, args.depth)

                # We save the game as pgn
                print(game, file=open("%s.pgn"%(output_filename), "w"), end="\n\n")

            else: #export raw tree
                export_raw_tree(tree, output_filename)

    cache._wait()
                
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nExiting...")