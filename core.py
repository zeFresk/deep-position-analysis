import io
import sys
import copy

from misc import *
from uci import *
from multipv import *

###########################################
####### Core functions & exploration ######
###########################################

class Explorator(object):
    def __init__(self):
        """Create an empty Explorator"""
        # Variables used to avoid copy (as if we copied the stack)
        self.engine = None
        self.cache = None
        self.pv = None
        self.nodes = None
        self.msec = None
        self.threshold = None
        self.appending = None

        # Variables used globally
        self.crashed_once = None
        self.tot = None
        self.time_st = None
        self.info_handler = None
        self.pos_index = None
        self.out = None
        self.fen_results = None

    async def explore(self, board, engine, cache, pv, depth, nodes, msec = None, threshold = 25600,appending = True):
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
        self.cache = cache
        self.pv = pv
        self.nodes = nodes
        self.msec = msec
        self.threshold = threshold/100
        self.appending = appending
        ##################
        # Here are all the variables commons to all recursions
        self.crashed_once = False # Needed to not print too much errors in case of a crash
        self.tot = pv.max_nodes_from(board, depth) # total number of nodes in the final tree, worst case scenario.

        self.time_st = time.perf_counter() # We initialize starting time

        self.info_handler = chess.uci.InfoHandler() # We will communicate with the engine using this
        self.engine.info_handlers.append(self.info_handler) 

        self.pos_index = 0 # Number of variations already explored

        self.fen_results = dict() # (hash_128) -> [(PV,score),...,(PVN,scoreN)]

        sys.stdout.buffer.close = lambda: None # atrocity but needed
        self.out = io.TextIOWrapper(sys.stdout.buffer, line_buffering = False) # We create a common non-buffered output

        #################
        # We then need to call the main function
        ret = await self._explore_rec(board, depth)
        if cache != None:
            await self.cache.wait_write()
        return ret


    async def _explore_rec(self, board, depth): # less parameters so less copy
        """Main recursive function."""
        #try:
        if depth == 0:
            return None

        self.pos_index += 1

        hf = hash_fen(board.fen())

        # Check if position has already been encountered
        if hf in self.fen_results:
            self.display_global_progress()
            self.display_cached_progress(board)
            self.tot -= self.pv.max_nodes_from(board, depth) # We need to update its value because less nodes need to be explored
            return None #terminal node

        # Start search in cache
        if self.cache != None and self.nodes != None:
            await self.cache.search_fen(self.nodes, hf, self.pv.get_pvs_from(board, depth))

        # Setting-up position for engine
        self.engine.position(board)
        # Start search
        cmd = self.engine.go(nodes=self.nodes, movetime=self.msec, async_callback=True)
        self.display_global_progress()

        while not cmd.done(): # until search is finished
            if self.cache != None and self.cache.fen_found(hf): # found in cache
                self.engine.stop()
                break

            time.sleep(0.00001) # Sleep for 10 µs to not use full core
            self.display_position_progress(board)

        # Get pvs
        pvs = None
        if self.cache != None and self.cache.fen_found(hf): # found in cache
            pvs = self.cache.fetch_pvs(hf)
            self.fen_results[hf] = keep_firstn(pvs, self.pv.get_pvs_from(board, depth)) # Delete uneeded pvs
            self.display_cached_progress(board)
        else:
            pvs = self.get_all_pvs(board, depth) # We extract all PVs available
            self.fen_results[hf] = keep_firstn(pvs, self.pv.get_pvs_from(board, depth)) # Delete uneeded pvs
            self.display_position_progress(board, end="\n\n") # Needed if we don't want the line to be blank in case it finished too fast

        # add them to cache if set
        if self.cache != None and self.nodes != None:
            await self.cache.save_fen(board.fen(), self.nodes, self.pv.max_pv(), pvs)

        for (pv, score) in self.fen_results[hf]: # explore new moves
            new_board = copy.deepcopy(board) # We copy the current board
            mo = pv[0] # First move in PV

            if not new_board.is_legal(mo): # If the next move is illegal (it can happen with Leela)
                raise RuntimeError("Illegal move : {:s} in {:s}\n".format(new_board.san(mo), new_board.fen())) # We throw an exception

            new_board.push(mo)
            if not new_board.is_game_over(claim_draw=True) and not self.above_threshold(score): # If the game isn't drawn or won by a player we continue
                await self._explore_rec(new_board, depth-1)
            else:
                self.tot -= self.pv.max_nodes_from(board, depth) # We need to update its value because less nodes need to be explored
    
        return self.fen_results

        #except KeyboardInterrupt as e:
        #    raise e
        #except SystemExit as e:
        #    raise e
        #except :
        #    if not self.crashed_once: # We only print the bug message if we are in the first recursive call
        #        print("\nCongratulations, you found a bug ! A bug report is generated in bug.log\nPlease help me correct it by linking the report to your message :)\n")
        #        self.crashed_once = True
        #        self.log_bug("bug.log", board, depth, sys.exc_info())

        #    raise

    def log_bug(self, filename, board, depth, exc_tuple):
        """Log an exception which occured in a given board to a file."""
        exc_type, exc_value, exc_traceback = exc_tuple # get full exception with traceback
        fbug = open("bug.log", "a")
        exception_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)) # We format the exception before saving it

        fbug.write("bug in fen = [{!s}] with \"{!s}\", PV={:d} NODES={:d} DEPTH={:d}\n####\n{!s}\n\n".format(board.fen(), self.engine.name, self.pv, self.nodes, depth, exception_str))

    def above_threshold(self, score):
        """Returns wether a score is above threshold or not."""
        if score[1] == "M": # This a mate score !
            return 128.0 > self.threshold # A mate value is 128
        else:
            return abs(float(score)) > self.threshold

    def get_all_pvs(self, board, depth):
        """Returns all the first moves computed and update total number of nodes to explore if needed."""
        ret = []
        with self.info_handler: # We need to lock the handler
            if self.info_handler.info["multipv"] < self.pv.get_pvs_from(board,depth): #less pv generated than requested, whatever the reason
                self.tot -= self.pv.max_nodes_from(board, depth-1)*(self.pv.get_pvs_from(board,depth) - self.info_handler.info["multipv"]) # We need to update its value because less nodes need to be explored
            for i in range(1, self.info_handler.info["multipv"]+1):
                ret += [[self.info_handler.info["pv"][i], self.get_pv_score(board, i)]]
        
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
        #with self.info_handler: # Waiting for the handler to be locked
        if "nodes" in self.info_handler.info and "pv" in self.info_handler.info and "nps" in self.info_handler.info and "score" in self.info_handler.info: # Make sure all values are set
                
            prct = 0
            if self.nodes != None: #we use nodes as stop
                prct = int(self.info_handler.info["nodes"])/self.nodes
            else: # we use time as stop
                prct = int(self.info_handler.info["time"])/self.msec

            if prct >= 1.00: # we can't exceed 100% !
                prct = 1.00

            self.out.write("\r" + " "*40) # cleaning line
            self.out.write("\r>> {:.0%} @ {:s}nodes/s : {:s} ({:s}){:s}".format(prct, format_nodes(int(self.info_handler.info["nps"])), current_board.san(self.info_handler.info["pv"][1][0]), self.get_pv_score(current_board, 1), end))
            self.out.flush()

    def display_cached_progress(self, current_board):
        """Display progress made from cached position. Fast. Suppose board IS in dictionnary"""
        self.out.write("\r" + " "*40) # cleaning line
        deb = self.get_pv_cached(current_board, 0)
        hf = hash_fen(current_board.fen())
        self.out.write("\r>> {:.0%} @ {:s}nodes/s : {:s} ({:s})\n\n".format(1., ".Inf", current_board.san(self.get_pv_cached(current_board, 0)[0]), self.get_pv_score_cached(current_board, 0)))
        self.out.flush()

    def get_pv_score(self, board, i):
        """Returns score associated to i-th PV formatted as a string. !!! WE SUPPOSE HANDLER IS LOCKED !!!"""
        return normalized_score_str(board, self.info_handler.info["score"][i].cp, self.info_handler.info["score"][i].mate)

    def get_pv_cached(self, board, i):
        """Returns PV in dictionnary."""
        return self.fen_results[hash_fen(board.fen())][i][0]

    def get_pv_score_cached(self, board, i):
        """Returns score associated to i-th PV formatted as a string."""
        return self.fen_results[hash_fen(board.fen())][i][1]
