#!/usr/bin/env python3

import sys, subprocess, os
import fhutils

def main():
    global server, port,ssl
    config = fhutils.GameConfig()
    data_dir = os.getcwd()  # Adding the ability to call from the game's directory
    game_stub = config.gameslist[0]['stub']
    try:
       game = fhutils.Game()
    except IOError:
        print("Could not read fh_names")
        sys.exit(2)
    
    if not os.path.isdir(data_dir):
        print("Sorry data directory %s does not exist." % (data_dir))
        sys.exit(2)
    
    for player in game.players:
        orders = "%s/sp%s.ord" %(data_dir, player['num'])
        try:
            with open(orders, "r+") as f:
                text = f.read()
                f.truncate(0)
                text2 = os.linesep.join([s for s in text.splitlines() if s])
                f.seek(0)
                #f.write(text2) # removed
                if not text2.isspace():
                    f.write(text2)
            f.close()
        except IOError:
            print("Couldn't open %s" %(orders))
                
if __name__ == "__main__":
    main()
