#  Cutoff  expression
# Because you want to be able to cut of moves only for one side, or only after x ply, or only after x ply
#
# Examples:
# - basic: 50 => 50 centipawns
# - one-sided: 50W => 50 centipawns only when it is white to play
# - after x moves: 50a10 => 50 centipawns after 10th move
# - before x moves: 50u5 => 50 centipawns until (included) 5th move
#
# Note: an expression must follow INTEGER[uINT][aINT)[WwBb]

import re
from misc import str_to_score
from chess import WHITE, BLACK

class Cutoff:
    wafter = None
    bafter = None
    wuntil = None
    buntil = None
    wc = None
    bc = None

    def __init__(self, expression):
        """Create a cutoff from an expression."""
        re_basic = re.compile(r"""^\d+$""")
        re_white = re.compile(r"""^(?:.*[bB])*(.+)[wW](?:.*[bB])*$""")
        re_black = re.compile(r"""^(?:.*[wW])*(.+)[bB](?:.*[wW])*$""")
        re_extract = re.compile(r"""^(\d+)(?:u(\d+))*(?:a(\d+))*$""")

        m = re_basic.match(expression)
        if m: # numeric expression
            self.bc = self.wc = int(m.group(0))
            self.wuntil = self.wafter = self.buntil = self.bafter = None
        elif re_extract.match(expression): # complex, no colors
            m = re_extract.match(expression) # no := operator because of 3.7 compatibility...
            self.wc = self.bc = int(m.group(1))
            self.buntil = self.wuntil = (None if m.lastindex < 2 else int(m.group(2)))
            self.bafter = self.wafter = (None if m.lastindex < 3 else int(m.group(3)))

        else:
            m = re_white.match(expression)
            if m: # white part
                m = re_extract.match(m.group(1))
                self.wc = int(m.group(1))
                self.wuntil = None if m.lastindex < 2 else int(m.group(2))
                self.wafter = None if m.lastindex < 3 else int(m.group(3))

            m = re_black.match(expression)
            if m: # black part
                m = re_extract.match(m.group(1))
                self.bc = int(m.group(1))
                self.buntil = None if m.lastindex < 2 else int(m.group(2))
                self.bafter = None if m.lastindex < 3 else int(m.group(3))

    def cut_pvs(self, pvs, move, color):
        """Eliminate pvs based on cutoff expression"""
        val = 0
        if color == WHITE:
            if (self.wafter != None and move < self.wafter) and (self.wuntil != None and move > self.wuntil):
                return pvs
            else:
                val = self.wc
        else:
            if (self.bafter != None and move < self.bafter) and (self.buntil != None and move > self.buntil):
                return pvs
            else:
                val = self.bc

        if val != None:
            # We suppose 1st = bestmove
            max_score = str_to_score(pvs[0][1])
            ret = []
            for pv in pvs:
                _, score = pv
                score = str_to_score(score)

                if max_score["mate"] != None: #mate
                    if score["mate"] != None and score["mate"] == max_score["mate"]:
                        ret += [pv]
                else:
                    if abs(max_score["cp"]-float(score["cp"])) <= (val/100.):
                        ret += [pv]

            return ret
        else:
            return pvs
