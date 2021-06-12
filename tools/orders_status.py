#!/usr/bin/env python

import sys, subprocess, os
import fhutils

def main():
    global server, port,ssl
    config = fhutils.GameConfig()
    data_dir = os.getcwd() # Adding the ability to call from the game's directory
    game_stub = config.gameslist[0]['stub']
    try:
       game = fhutils.Game()
    except IOError:
        print("Could not read fh_names")
        sys.exit(2)
    
    if not os.path.isdir(data_dir):
        print("Sorry data directory %s does not exist." % (data_dir))
        sys.exit(2)
    longest_name = len(max([x['name'] for x in game.players], key=len))
    for player in game.players:
        name = player['name'].center(longest_name)
        orders = "%s/sp%s.ord" %(data_dir, player['num'])
        try:
            with open(orders, "r+") as f:
                print(type(f))
                test = f.read()
                test = test.encode("UTF-8")
                print(type(test))
                p = subprocess.Popen(["/usr/bin/perl", "/home/jason/Documents/Far-Horizons/src/fh/engine/bash/orders.pl"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                #test = test.encode('utf-8')
                verify = p.communicate(input=test)[0]
                verify = verify.decode('utf-8')
                print(type(verify))
                if "No errors found" in verify:
                    print("%s - %s - Ready" %(player['num'], name))
                else:
                    print("%s - %s - Errors" %(player['num'], name))
        except IOError:
            print("%s - %s - No Orders" %(player['num'], name))
                
if __name__ == "__main__":
    main()
