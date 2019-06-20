import re

###########################################
################ Threshold ################
###########################################

### Threshold expression :
# Either a number in PAWNS, integer or float at which you don't want to explore further
# Or an unicolor threshold :
    # 5W for example will stop exploration if white has more than 5 PAWNS advantage
    # Note : The advantage of the other color will be ignored
# Or a bicolor threshold :
    # 1W5B : will stop if white is 1 pawn ahead OR if black is 5 pawns ahead.

def parse_threshold_exp(exp):
    """Try to extract data from threshold expression."""
    # Regex used
    number = r"(\d+(?:\.\d*)?)"
    color = r"([WwBb])"
    half = number + color
    full = half + half

    re_number = re.compile(r"^"+number+r"$")
    re_half = re.compile(r"^"+half+r"$")
    re_full = re.compile(r"^"+full+r"$")

    # Parsing
    if exp == "": # Empty threshold
        return (float("-inf"), float("inf"))

    m = re_number.match(exp)
    if m != None: # exp is just a number : 5
        return (-float(m[1]), float(m[1]))

    m = re_half.match(exp)
    if m != None: # exp is a half expression : 5B
        if m[2] in "Ww": #5W
            return (float("-inf"), float(m[1]))
        else: #5B
            return (-float(m[1]), float("inf"))

    m = re_full.match(exp)
    if m != None: # full exp : 5B4W
        if m[2] == m[4]: # same color
            return (None, None)
        else:
            if m[2] in "Ww": #5W4B
                return (-float(m[3]), float(m[1]))
            else: #5B4W
                return (-float(m[1]), float(m[3]))

    return (None, None) # No match => ill formed expression

def finf(lhs, rhs, epsilon=0.00001):
    """Return lhs < rhs"""
    return rhs-lhs > epsilon


class Threshold(object):
    def __init__(self, exp):
        """ 
        Create a Threshold object from an expression.
        exp : threshold expression (5 or 5W or 5W5B)
        """
        self.min, self.max = parse_threshold_exp(exp)
        if self.min == None or self.max == None: # Error occured when parsing
            raise Exception("Threshold expression: '{:s}' is invalid.".format(exp))

    def above_threshold(self, value):
        """Check if given is above threshold."""
        # We use floating point number here so we have to take care
        return finf(value,self.min) or finf(self.max,value) 