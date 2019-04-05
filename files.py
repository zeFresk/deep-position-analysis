import chess.pgn

from misc import * # is_pgn...

###########################################
############## File parsing ###############
###########################################

def fens_from_file(filename):
    """Extract all the fen inside a .pgn or .epd"""
    file = open(filename, "r")
    fens = []

    if is_pgn(filename): # pgn input detected we will skip through last position
        print("PGN input detected we will only analyze from last position(s) reached.")

        game = chess.pgn.read_game(file)
        while game != None: # there is still at least one game to parse
            board = game.board() # set up board to initial position

            for move in game.main_line(): # iterate through mainline
                board.push(move)

            fens += [board.fen()]
            game = chess.pgn.read_game(file) # try to 
    else: #standard .fen or .epd
        raw_lines = file.readlines()
        for l in raw_lines: #extract all fen
            fen = extract_fen(l)
            
            if fen != None: # If we found a fen
                fens += [fen]

    return fens

def format_filename(filename, id, args):
    """Returns the output filename given input filename, index and args."""
    index = filename.find(".")
    if index == -1:
        index = len(filename)

    stopping_fmt = (format_nodes(args.nodes,"{:1.0f}") +"n") if (args.nodes != None) else (str(args.sec)+"s")
    return "%s%d_%s%dv%dp"%(filename[0:index], id, stopping_fmt, args.pv, args.depth)

def new_default_game(board, engine_name, args):
    """Returns a Game object with the default headers and board set."""
    game = chess.pgn.Game()
    stopping = (format_nodes(args.nodes,"{:1.0f}") +" nodes") if (args.nodes != None) else (str(args.sec)+" seconds")
    game.headers["Event"] = "DeA using {:s} at {:s} per move, {:d} PV, {:d} ply-depth, of {:s}".format(engine_name, stopping, args.pv, args.depth, board.fen())
    game.headers["White"] = engine_name
    game.headers["Black"] = engine_name           

    game.setup(board)

    return game

def load_ith_from_pgn(filename, i):
    """Returns the i-th game of a given pgn named 'filename'."""
    file_tmp = open(filename) # we reload pgn

    game = chess.pgn.read_game(file_tmp)
    for _ in range(i): # skip to i-th game in pgn
        game = chess.pgn.read_game(file_tmp)

    return game

def export_raw_tree(tree, filename): # Warning : Ugly, need to be improved
    """Export a tree object to a new file called filename."""
    # We save the tree
    print(tree, file=open("%s.tree"%(output_filename), "w"), end="\n")

    #delete artefacts
    f = open("%s.tree"%(output_filename), "r")
    lines = f.readlines()
    f.close()
    out = open("%s.tree"%(output_filename), "w")

    reg = r"Move\.from_uci\(\'(\w+)\'\)"
    for l in lines:
        l = re.sub(reg, r"\1", l)
        l = l.replace("(", "{")
        l = l.replace(")", "}")
        l = l.replace("[", "{")
        l = l.replace("]", "}")
        out.write(l)

###########################################
######### Tree parsing functions ##########
###########################################

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