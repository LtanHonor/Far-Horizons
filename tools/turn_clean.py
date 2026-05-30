#!/usr/bin/env python3
"""
    Usage: turn_clean.py [-h] -c config.yml

    -h, --help      print this message
    -c config.yml   use a particular config file

    Minimal cleanup utility for turn-processing leftovers.
    It removes interspecies.dat and *.log files from the game data dir.
"""

import glob
import os
import sys
import getopt

import fhutils


def main(argv):
    config_file = None

    try:
        opts, _args = getopt.getopt(argv, "hc:", ["help", "config="])
    except getopt.GetoptError:
        print(__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif opt in ("-c", "--config"):
            config_file = arg

    if config_file:
        config = fhutils.GameConfig(config_file)
    else:
        config = fhutils.GameConfig()

    game = config.gameslist[0]  # for now we only support a single game
    data_dir = game["datadir"]

    if not os.path.isdir(data_dir):
        print("Sorry data directory %s does not exist." % (data_dir))
        sys.exit(2)

    removed = []

    interspecies_path = os.path.join(data_dir, "interspecies.dat")
    if os.path.isfile(interspecies_path):
        os.remove(interspecies_path)
        removed.append("interspecies.dat")

    for log_file in glob.glob(os.path.join(data_dir, "*.log")):
        try:
            os.remove(log_file)
            removed.append(os.path.basename(log_file))
        except OSError as exc:
            print("Could not remove %s: %s" % (log_file, exc))

    if removed:
        print("Removed %d file(s):" % (len(removed)))
        for name in sorted(removed):
            print("  - %s" % (name))
    else:
        print("Nothing to clean.")


if __name__ == "__main__":
    main(sys.argv[1:])
