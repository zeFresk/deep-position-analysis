import re
import chess

###########################################
########## Non constant MultiPV ###########
###########################################

### MultiPV expression :
# (N, M, K, V are integers in all the following expressions)
# N : White multiPV = N for each ply, same for black
# NwMb : White multiPV = N for each ply, black multiPV = M for each ply
# N[+-]K/Vp : MultiPV start at N and [increase/decrease] by K each V plies
# [...]w[...]b : same as above where [...] is a N[+-]K/Vp expression

def make_pv_from_match(matches):
    """Create half of the PV tuple from match object of a complex expression."""
    inc = 1 if matches[3] == "" else int(matches[3])
    return (int(matches[1]), int(matches[2]), inc)

def parse_pv_exp(pv_exp):
    """
    Parse a MultiPV expression.
    Returns a couple :
    ((white_pv at start, increase, plies before increase),(black_pv at start, increase, plies before increase))
        if the expression is correct.
    else returns None.
    """
    # Regex definitions
    digit_only = r"^(\d+)$"
    re_digit_only = re.compile(digit_only)

    complex_expression = r"^(\d+)([+-]\d+)[/e]?(\d*)[mM]?$"
    re_cexp = re.compile(complex_expression)

    composed_expression = r"^(" \
        + digit_only[1:-1].replace("(","").replace(")","") \
        + r"|" + complex_expression[1:-1].replace("(","").replace(")","") \
    + r")([WwBb])("  \
        + digit_only[1:-1].replace("(","").replace(")","") \
        + r"|" + complex_expression[1:-1].replace("(","").replace(")","") \
    + r")([WwBb])$"

    def parse_singleton(pv_subexp):
        sub_m = re_digit_only.match(pv_subexp)
        if sub_m != None: # number singleton
            return (int(sub_m[1]), 0, 1)

        sub_m = re_cexp.match(pv_subexp)
        if sub_m != None: # complex expression
            return make_pv_from_match(sub_m)

    m = parse_singleton(pv_exp)
    if m != None: # singleton
        return (m, m)
    
    m = re.match(composed_expression, pv_exp) # expression is composed of two singletons
    lhs = parse_singleton(m[1])
    rhs = parse_singleton(m[3])
    if lhs == None or rhs == None: # one of them is incorrect
        return None
    else:
        if m[2] in "Ww" and m[4] in "Bb": #WB
            return (lhs, rhs)
        elif m[2] in "Bb" and m[4] in "Ww": #BW
            return (rhs, lhs)
    
    return None # exp does not match


class MultiPV(object):
    """Contains and calculate PV for all depths."""
    class __Cached(object): # Hide cached data
        def __init__(self, array, depth):
            self.white_pvs = [None for _ in range(depth)]
            self.black_pvs = [None for _ in range(depth)]
            self.white_max_nodes = [None for _ in range(depth)]
            self.black_max_nodes = [None for _ in range(depth)]

            self.generate_pvs(array)
            self.generate_max_nodes()

            self.max_pv = max(max(self.black_pvs), max(self.white_pvs))

        def generate_pvs(self, array):
            (w_base, w_increase, w_each), (b_base, b_increase, b_each) = array #unpack
            # White
            for i in range(len(self.white_pvs)):
                self.white_pvs[len(self.white_pvs)-1-i] = max(w_base + int((i/(w_each*2)))*w_increase, 1)
            # Black
            for i in range(len(self.black_pvs)):
                self.black_pvs[len(self.black_pvs)-1-i] = max(b_base + int((i/(b_each*2)))*b_increase, 1)

        def __get_pvs(self, color, depth):
            if color == chess.WHITE:
                return self.white_pvs[depth]
            else:
                return self.black_pvs[depth]

        def __recursive_gen(self,color, depth):
            if depth == 0:
                return 1
            pv_i = self.__get_pvs(color, depth)
            return 1 + pv_i * self.__recursive_gen(not color, depth-1)
        
        def generate_max_nodes(self):
            """Generate max numbers of nodes for each depth. 
            Need optimization if I have time to do so.
            Still under 100ms for depth=24 so..."""
            for i in range(len(self.white_max_nodes)):
                self.white_max_nodes[i] = self.__recursive_gen(chess.WHITE, i)
            for i in range(len(self.white_max_nodes)):
                self.black_max_nodes[i] = self.__recursive_gen(chess.BLACK, i)
            #self.white_max_nodes[0] = 1
            #self.black_max_nodes[0] = 1
            ## White
            #turn = chess.WHITE
            #for i in range(1,len(self.white_pvs)):
            #    self.white_max_nodes[i] = self.white_max_nodes[i-1]*self.__get_pvs(turn, i) +1
            #    turn = not turn
            ## White
            #turn = chess.BLACK
            #for i in range(1,len(self.white_pvs)):
            #    self.black_max_nodes[i] = self.black_max_nodes[i-1]*self.__get_pvs(turn, i) +1

        def __max_nodes(self, color, depth): # No check
            if color == chess.WHITE:
                return self.white_max_nodes[depth]
            else:
                return self.black_max_nodes[depth]

        def get_max_nodes(self, color, depth):
            return self.__max_nodes(color, depth-1)

        def get_pvs(self, color, depth):
                return self.__get_pvs(color, depth-1)


    def __init__(self, pv_exp, max_depth):
        """
        Initialize multiPV given a multiPV expression (see above) 
        and the maximum_depth possible.
        """
        self.str = pv_exp # ? Maybe simplify it to minimum in the future ?
        self.base_array = parse_pv_exp(pv_exp)
        self.max_depth = max_depth
        self.__cached = self.__Cached(self.base_array, self.max_depth) # Create cache

        if self.base_array == None or self.base_array == (None,None): # pv_exp is not a valid expression
            raise Exception("pv_exp is not a valid MultiPV expression!")

    def max_nodes(self, color, depth):
        """Returns max possibles nodes if its 'color' turn and we are at depth 'depth'."""
        if depth < 1:
            return 1
        return self.__cached.get_max_nodes(color, depth)

    def max_nodes_from(self, board, depth):
        """Returns max possible number of moves starting from 'board' with 'depth' plies left."""
        return self.max_nodes(board.turn, depth)

    def get_pvs(self, color, depth):
        """Returns pvs if it's 'color' turn at depth 'depth'."""
        if depth < 1:
            return 1
        return self.__cached.get_pvs(color, depth)

    def get_pvs_from(self, board, depth):
        """Returns pvs from 'board' at depth 'depth'."""
        return self.get_pvs(board.turn, depth)

    def max_pv(self):
        """Returns biggest Multi-PV needed."""
        return self.__cached.max_pv

    def to_str(self):
        """Converts this to a PV expression."""
        return self.str

    def to_file_str(self):
        """Returns this to a PV expression suitable in a filename."""
        ret = self.str.replace("/","e")
        ret = ret.lower()
        ret = ret.replace("w","W")
        ret = ret.replace("b","B")
        return ret
