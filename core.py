import io
import sys
import copy

from misc import *
from uci import *
from multipv import *
from threshold import *

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
        self.plydepth = None
        self.threshold = None
        self.appending = None

        # Variables used globally
        self.crashed_once = None
        self.tot = None
        self.time_st = None
        self.info_handler = None
        self.pos_index = None
        self.cached_found = None
        self.out = None
        self.fen_results = None

    async def explore(self, board, engine, cache, pv, depth, nodes, msec = None, plydepth = None, threshold = Threshold(""),appending = True):
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
        self.plydepth = plydepth
        self.threshold = threshold
        self.appending = appending
        ##################
        # Here are all the variables commons to all recursions
        self.crashed_once = False # Needed to not print too much errors in case of a crash
        self.tot = pv.max_nodes_from(board, depth) # total number of nodes in the final tree, worst case scenario.

        self.time_st = time.perf_counter() # We initialize starting time

        self.info_handler = chess.uci.InfoHandler() # We will communicate with the engine using this
        self.engine.info_handlers.append(self.info_handler) 

        self.pos_index = 0 # Number of variations already explored
        self.cached_found = 0 # Number of positions found in cache (needed to get accurate time estimates)
        self.avg_nps = 0 # Average nodes per second

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

        hf = hash_fen(board.fen())

        # Check if position has already been encountered
        if hf in self.fen_results:
            self.cached_found += 1
            self.display_global_progress()
            self.display_cached_progress(board)
            if depth != 1:
                self.delete_subnodes(board, depth) # We need to update its value because less nodes need to be explored
            self.pos_index += 1
            return None #terminal node

        # Start search in cache
        if self.cache != None:
            tmp_nodes = self.nodes
            if self.msec != None:
                if self.avg_nps > 0:
                    tmp_nodes = self.avg_nps * self.msec * 1000
                else:
                    tmp_nodes = sys.maxsize

            await self.cache.search_fen(tmp_nodes, self.msec, self.plydepth, hf, self.pv.get_pvs_from(board, depth))


        # Setting-up position for engine
        self.engine.position(board)
        # Start search
        cmd = self.engine.go(nodes=self.nodes, movetime=self.msec, depth=self.plydepth, async_callback=True)
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
            self.cached_found += 1
            pvs = self.cache.fetch_pvs(hf)
            self.fen_results[hf] = keep_firstn(pvs, self.pv.get_pvs_from(board, depth)) # Delete uneeded pvs
            self.display_cached_progress(board)
        else:
            if self.msec is not None:
                self.update_nps()

            pvs = self.get_all_pvs(board, depth) # We extract all PVs available
            self.fen_results[hf] = keep_firstn(pvs, self.pv.get_pvs_from(board, depth)) # Delete uneeded pvs
            self.display_position_progress(board, end="\n\n") # Needed if we don't want the line to be blank in case it finished too fast

        # add them to cache if set
        if self.cache != None:
            if not self.cache.fen_found(hf): # fix bug with infinite wait if nodes too low !!Optimizable
                await self.cache.save_fen(board.fen(), self.nodes, wait_for(self.info_handler, "nodes"), self.msec, self.plydepth, self.pv.max_pv(), pvs)

        self.pos_index += 1

        for (pv, score) in self.fen_results[hf]: # explore new moves
            new_board = copy.deepcopy(board) # We copy the current board
            mo = pv[0] # First move in PV

            if not new_board.is_legal(mo): # If the next move is illegal (it can happen with Leela)
                raise RuntimeError("Illegal move : {:s} in {:s}\n".format(new_board.san(mo), new_board.fen())) # We throw an exception

            new_board.push(mo)
            if not new_board.is_game_over(claim_draw=True) and not self.above_threshold(board, score): # If the game isn't drawn or won by a player we continue
                await self._explore_rec(new_board, depth-1)
            else:
                self.delete_subnodes(board, depth-1) # We need to update its value because less nodes need to be explored
    
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

    def delete_subnodes(self, board, depth):
        """
        Need to be called when we will not exoplore further a variation. Whatever the reason.
        Remove subtree size from the total to search.
        """
        self.tot -= self.pv.max_nodes_from(board, depth-1)


    def above_threshold(self, board, score):
        """Returns wether a score is above threshold or not."""
        if score[1] == "M": # This a mate score !
            return self.threshold.above_threshold(normalize(board, 128)) # A mate value is 128
        else:
            return self.threshold.above_threshold(normalize(board, float(score[1:])))

    def get_all_pvs(self, board, depth):
        """Returns all the first moves computed and update total number of nodes to explore if needed."""
        ret = []
        with self.info_handler: # We need to lock the handler
            multipv = 1 if "multipv" not in self.info_handler.info else self.info_handler.info["multipv"] # If no "multipv" it indicates that MultiPV = 1
            if multipv < self.pv.get_pvs_from(board,depth): #less pv generated than requested, whatever the reason
                for j in range(self.pv.get_pvs_from(board,depth) - multipv): # We need to update its value because there's less nodes need to explore
                    self.delete_subnodes(board, depth-1)
            for i in range(1, multipv+1):
                ret += [[self.info_handler.info["pv"][i], self.get_normalized_pv_score_str(board, i)]]
        
        return ret

    def display_global_progress(self):
        """Display the global progress in analyzing all the possible variations along with estimated time needed."""
        elapsed_time = elapsed_since(self.time_st) # Getting elapsed time from start

        calculated_pos = max(self.pos_index - self.cached_found, 0)
        pos_per_s = calculated_pos/elapsed_time # average positions per second
        remaining_time_seconds = int((self.tot-(self.pos_index)) / pos_per_s) if pos_per_s > 0 else 0
        remaining_time_str = "{:d}h {:d}m".format(remaining_time_seconds // (60*60), (remaining_time_seconds // 60) %60) if remaining_time_seconds > 0 else "calculating"
        print(">Analysing variation {:d} of {:d}, estimated time remaining : {:s}...".format(self.pos_index+1, self.tot, remaining_time_str), flush=True)
        self.out.write(">> 0% : ###")

    def display_position_progress(self, current_board, end=""):
        """Display the progress analyzing the current position. Can take a lot of time since we need to lock a mutex."""
        #with self.info_handler: # Waiting for the handler to be locked
        if "nodes" in self.info_handler.info and "pv" in self.info_handler.info and "nps" in self.info_handler.info and "score" in self.info_handler.info and 1 in self.info_handler.info["pv"] and "depth" in self.info_handler.info: # Make sure all values are set
                
            prct = 0
            if self.nodes != None: #we use nodes as stop
                prct = int(self.info_handler.info["nodes"])/self.nodes
            elif self.msec != None: # we use time as stop
                prct = int(self.info_handler.info["time"])/self.msec
            elif self.plydepth != None:
                prct = int(self.info_handler.info["depth"])/self.plydepth

            if prct >= 1.00: # we can't exceed 100% !
                prct = 1.00

            self.out.write("\r" + " "*40) # cleaning line
            self.out.write("\r>> {:.0%} @ {:s}nodes/s : {:s} ({:s}){:s}".format(prct, format_nodes(int(self.info_handler.info["nps"])), current_board.san(self.info_handler.info["pv"][1][0]), self.get_normalized_pv_score_str(current_board, 1), end))
            self.out.flush()

    def display_cached_progress(self, current_board):
        """Display progress made from cached position. Fast. Suppose board IS in dictionnary"""
        self.out.write("\r" + " "*40) # cleaning line
        deb = self.get_pv_cached(current_board, 0)
        hf = hash_fen(current_board.fen())
        self.out.write("\r>> {:.0%} @ {:s}nodes/s : {:s} ({:s})\n\n".format(1., ".Inf", current_board.san(self.get_pv_cached(current_board, 0)[0]), self.get_pv_score_cached(current_board, 0)))
        self.out.flush()

    def get_normalized_pv_score_str(self, board, i):
        """Returns score associated to i-th PV formatted as a string. !!! WE SUPPOSE HANDLER IS LOCKED !!!"""
        return normalized_score_str(board, self.info_handler.info["score"][i].cp, self.info_handler.info["score"][i].mate)

    def get_pv_cached(self, board, i):
        """Returns PV in dictionnary."""
        return self.fen_results[hash_fen(board.fen())][i][0]

    def get_pv_score_cached(self, board, i):
        """Returns score associated to i-th PV formatted as a string."""
        return self.fen_results[hash_fen(board.fen())][i][1]

    def update_nps(self):
        """Update average nps with latest nodes computed."""
        self.avg_nps = (self.pos_index/(self.pos_index+1))*self.avg_nps + (1/(self.pos_index+1))*wait_for(self.info_handler,"nps")
