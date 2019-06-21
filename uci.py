import chess.uci
import sys
import os

###########################################
########## UCI config functions ###########
###########################################

def write_config(opt, file):
    """Export options dictionnary to config file."""
    for key, value in opt.items():
        if key.lower() == "multipv":
            continue

        file.write("{:s} = {:s}\n".format(str(key), str(value)))

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
    """ 
    Load engine uci options from config, 
    if no config exists will create one. 
    Returns a tuple : (config , boolean containing whereas or not we used a default config)"""
    if config == "<autodiscover>": #no config provided
        engine_name = engine.name.split()[0] # first string in name
        config = engine_name + ".cfg"

        if not os.path.isfile(config): # no existing config file
            print("\n!Warning: No config file for {:s} detected, creating one. Default values used.\n".format(engine_name))
            f = open(config, "w")

            opt = default_options(engine)
            write_config(opt, f) # exporting config to file

            return (opt, True)

    if os.path.isfile(config): # custom or default config exists
        opt = default_options(engine)

        f = open(config, "r")
        update_options_from_config(opt, f)
        return (opt, False)

    else: #no config found
        sys.stderr.write("!!Error: config {:s} doesn't exists ! Exiting...\n")
        sys.exit(-2)
