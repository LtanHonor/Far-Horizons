#!/usr/bin/env python3
"""

 The following script will auto-generate galaxy using data piped via stdio
 Player data is expected in the following format(one line per player):

 email,sp_name,home_planet_name,gov_name,gov_type,ML,GV,LS,BI

 See example.csv for example

 Execute from game directory: game_setup.py < ../example.csv

"""

import fhutils
import os, tempfile, subprocess, sys, shutil, csv
import getopt


def validate_signup_row(row, row_index):
    max_text_len = 128
    if len(row) != 9:
        raise ValueError(
            "CSV row %d must have 9 fields: email,species,home_planet,gov_name,gov_type,ML,GV,LS,BI"
            % row_index
        )

    email, sp_name, home_planet, gov_name, gov_type, ML, GV, LS, BI = [x.strip() for x in row]

    for label, value in [
        ("species", sp_name),
        ("home_planet", home_planet),
        ("gov_name", gov_name),
        ("gov_type", gov_type),
    ]:
        if len(value) == 0:
            raise ValueError("CSV row %d: field '%s' cannot be empty" % (row_index, label))
        if len(value) > max_text_len:
            raise ValueError(
                "CSV row %d: field '%s' exceeds %d chars (%d): %s"
                % (row_index, label, max_text_len, len(value), value)
            )

    tech_values = {}
    for label, value in [("ML", ML), ("GV", GV), ("LS", LS), ("BI", BI)]:
        if not value.isdigit():
            raise ValueError("CSV row %d: field '%s' must be an integer: %s" % (row_index, label, value))
        numeric_value = int(value)
        if numeric_value < 0 or numeric_value > 15:
            raise ValueError(
                "CSV row %d: field '%s' must be between 0 and 15 (got %d)"
                % (row_index, label, numeric_value)
            )
        tech_values[label] = numeric_value

    tech_total = tech_values["ML"] + tech_values["GV"] + tech_values["LS"] + tech_values["BI"]
    if tech_total != 15:
        raise ValueError(
            "CSV row %d: ML+GV+LS+BI must equal 15 (got %d)"
            % (row_index, tech_total)
        )

    return [email, sp_name, home_planet, gov_name, gov_type, ML, GV, LS, BI]

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

    reader = csv.reader(sys.stdin, delimiter=',')
    data = []
    for idx, row in enumerate(reader, start=1):
        if not row:
            continue
        if all(not cell.strip() for cell in row):
            continue
        try:
            clean_row = validate_signup_row(row, idx)
        except ValueError as exc:
            print("Input CSV validation error: %s" % exc)
            sys.exit(1)
        data.append(clean_row)

    num_species = len(data)

    print("%s species defined." % (num_species));

    print("Executing NewGalaxy ")

    # Galaxy size is calculated based on default star density and fixed number of stars per race
    # Adjust it here to create less crowded galaxy, players are asking for that
    adjusted_num_species = str(int(( num_species * 3) / 2))

    fhutils.run(bin_dir, "NewGalaxy", [adjusted_num_species])

    print("Executing MakeHomes")
    fhutils.run(bin_dir, "MakeHomes")

    print("Executing ListGalaxy")

    output = fhutils.run(bin_dir, "ListGalaxy", ["-p"])

    star_list = [s for s in output.splitlines() if s] # strips empty lines from output
    uniq_list = list(set(star_list))  # uniques the list
    if len(star_list) != len(uniq_list):
        print("Galaxy contains duplicate stars!!!")
        sys.exit(1)

    curr_sp_number = 1

    try:
        fh_names = open("fh_names", "w")
        fh_names.truncate()
    except IOError:
        print("cannot open fh_names")
        sys.exit(1)

    for col in data:
        email, sp_name, home_planet, gov_name, gov_type, ML, GV, LS, BI = col

        print("\t Executing HomeSystemAuto (%s) " % (curr_sp_number))
        output = fhutils.run(bin_dir, "HomeSystemAuto", ["12"])
        x,y,z,n = output.split(" ")

        print("\t Executing AddSpecies (%s) " % (curr_sp_number))
        arg = [ str(curr_sp_number), sp_name, home_planet, gov_name, gov_type, x, y, z, n, ML, GV, LS, BI]
        print(arg)
        output = fhutils.run(bin_dir, "AddSpeciesAuto", arg)

        try:
            fh_names.write("%02d\n%s\n%s\n" % (curr_sp_number, sp_name, email))
        except IOError:
            print("cannot write to fh_names")
            sys.exit(1)

        curr_sp_number += 1
    fh_names.close()

    print("\t Preparing Turn 1: executing Finish")
    fhutils.run(bin_dir, "Finish")
    print("\t Reporting Turn 1: executing Report")
    fhutils.run(bin_dir, "Report")
    print("DONE")

if __name__ == "__main__":
    main(sys.argv[1:])
