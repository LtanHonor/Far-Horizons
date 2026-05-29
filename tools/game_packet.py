#!/usr/bin/env python3
"""
    This script will create a zip file containing a first turn packet for a player.
"""
import fhutils
import os, sys, zipfile
import getopt

def main(argv):
    config_file = None
    discard = False
    try:                                
        opts, args = getopt.getopt(argv, "hc:", ["help", "config="])
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
    game = config.gameslist[0] # for now we only support a single game
    game_name = game['name']
    data_dir = game['datadir']
    bin_dir = config.bindir
    
    os.chdir(data_dir)
    
    # prepare galaxy list
    output = fhutils.run(bin_dir, "ListGalaxy", ["-p"])
    with open("galaxy.list.txt", "w") as f:
        f.write(output)
        
    players = fhutils.Game().players

    # Resolve policies file: prefer game_policies.pdf in game dir,
    # fall back to policies.txt in the gameDocs/ subdirectory.
    def _resolve_policies(data_dir: str) -> str | None:
        candidates = [
            os.path.join(data_dir, "game_policies.pdf"),
            os.path.join(data_dir, "gameDocs", "policies.txt"),
            os.path.join(data_dir, "game_policies.txt"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    policies_path = _resolve_policies(data_dir)

    # Files shared by every player packet (only included if they exist)
    SHARED_FILES = [
        "galaxy.map.pdf",
        "galaxy.map.txt",
        "galaxy.list.txt",
    ]

    for p in players:
        zip_name = "sp%s.zip" % p['num']
        rpt_name = "sp%s.rpt.t1.txt" % p['num']

        to_zip: list[tuple[str, str]] = []  # (abs_path, arcname)
        for fname in [rpt_name] + SHARED_FILES:
            fpath = os.path.join(data_dir, fname) if not os.path.isabs(fname) else fname
            if os.path.isfile(fpath):
                to_zip.append((fpath, fname))
            else:
                print("  skipping (not found): %s" % fname)

        if policies_path:
            to_zip.append((policies_path, os.path.basename(policies_path)))
        else:
            print("  skipping (not found): game_policies.pdf / gameDocs/policies.txt")

        try:
            with zipfile.ZipFile(zip_name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for fpath, arcname in to_zip:
                    zf.write(fpath, arcname)
            print("Created %s (%d file(s))" % (zip_name, len(to_zip)))
        except Exception as exc:
            print("ERROR making zip %s: %s" % (zip_name, exc))

if __name__ == "__main__":
    main(sys.argv[1:])
