import re
import time
import chess
import hashlib
import pickle

###########################################
############ Helper functions #############
###########################################

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

def format_time(msec):
    """Converts msec to correct unit. Returns it as formatted string."""
    if msec < 10**3: #ms
        return str(msec)+"ms"
    else:
        return str(msec//1000)+"s"

def elapsed_since(timestamp):
    """Returns elapsed time since a given timestamp in seconds.
    It will always returns at least one."""
    ret = time.perf_counter() - timestamp
    return ret if ret >= 1 else 1

def is_pgn(filename):
    """Tells if a filename is a pgn."""
    return filename[-4:] == ".pgn"

def extract_fen(str):
    """Try to extract a string from a string. Will strip comments and uneeded content.
    Returns None if str is not a valid fen, else returns the match"""
    regex = r"^.*?([\dpPrRnNbBqQkK\/]+\s+[bw]\s[KkQq-]*[\s-]+\d+\s+\d+).*$"
    match = re.search(regex, str)
    return match[1] if match != None else None

def normalize(board, num):
    """Returns num from white POV."""
    if board.turn == chess.WHITE: # it's white's turn
        return num
    else: # Black's turn
        return -num

def mate_to_cp(mate):
    return (mate/abs(mate))*128. # (sign of mate * 128)

def normalized_score_str(board, cp, mate):
    """Returns score as a string from white POV."""
    if mate != None: # Mate in X
        return fmt_mate(normalize(board, mate))
    else: # We only have a centipawn value
        return "{:+.2f}".format(normalize(board, cp)/100.)

def hash_fen(fen_str):
    """Hash a string and returns a 128-bytes number. Low collisions."""
    h = hashlib.md5()
    h.update(fen_str.encode("ascii")) #feed the fen to hash function
    return int.from_bytes(h.digest(), byteorder='little', signed=False) # Returns a big number


def hash_opt(options):
    ret = sorted(options) # We need to order them

    h = hashlib.md5()

    for k in ret:
        h.update(pickle.dumps(k))
        h.update(pickle.dumps(options[k]))

    return pickle.dumps(int.from_bytes(h.digest(), byteorder='little', signed=False), protocol=pickle.HIGHEST_PROTOCOL)

def remove_multiPV(opt):
    """delete MultiPV from the options"""
    del opt["MultiPV"]
    return opt

def blobify(obj):
    """To BLOB."""
    return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

def keep_firstn(lst, n):
    """Keep only the first n elems in a list."""
    if len(lst) <= n:
        return lst
    else:
        return lst[:n]

def wait_for(handler, k):
    """Returns handler.info[k] when it is available. Blocking."""
    while not k in handler.info:
        time.sleep(0.00001) # Sleep for 10 µs to not use full core

    return handler.info[k]