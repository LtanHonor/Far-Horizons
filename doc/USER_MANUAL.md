# Far Horizons User Manual

For a command-first daily workflow, see `doc/QUICK_OPS_CHEAT_SHEET.md`.

This manual combines and cleans up operational documentation from:

- `README.md`
- `INSTALL`
- `doc/gm_sequence`
- `tools/README.md`
- scripts in `tools/` and `bash/`
- command definitions in `src/fh.h`

It is focused on how to run and maintain a game as a Game Master (GM), plus a quick reference for player order commands.

## 1. What Is In This Repository

- `src/`: C source code for the Far Horizons engine.
- `bin/`: compiled engine commands (created from `src/`).
- `tools/`: modern Python GM utilities (recommended workflow).
- `bash/`: older shell/perl workflow (legacy, still useful for reference).
- `doc/`: rules and supporting docs.

## 2. Platform Requirements

### Recommended environment

A Unix-like environment (Linux/macOS/WSL) is recommended because many scripts assume:

- shell tools (`cp`, `zip`, etc.)
- Perl
- mail tooling (`mutt`) for legacy scripts

### Python

Use Python 3.10+.

Install Python packages from:

- `tools/pyrequirements.txt`

Typical install:

```bash
python3 -m pip install -r tools/pyrequirements.txt
```

### External tools used by map/packet workflows

- `ps2pdf` (ghostscript)
- `pdftk` or `pdfunite` (for map PDF merge)
- `zip`

## 3. Build The Engine

From repository root:

```bash
cd src
./make.all
```

This compiles binaries into `bin/`.

## 4. Core Data Files Used During Play

In each game data directory (example: `games/NEB`):

- `*.dat`: game state database files
- `spNN.ord`: player order files
- `spNN.rpt.tT.txt`: reports for species `NN`, turn `T`
- `fh_names`: 3-line repeating records of species number, species name, email

## 5. Recommended GM Workflow (Python Tools)

All commands below are run from the game data directory unless stated otherwise.

Most tools accept:

- `-h`, `--help`
- `-c`, `--config <file>` (optional custom config)

Default config filename expected by tools: `farhorizons.yml`.

### 5.1 New game setup

You can do this from the GUI with the **New Game Wizard** button, or with the command-line tools below.
If you collect signups by email, run `signups_fetch.py` first to generate the
CSV that `game_setup.py` consumes.
Use a subject line containing `FH <game stub> Signup` so the fetcher can
distinguish signup mail from normal turn traffic, for example `FH GA Signup`.
The subject match is tolerant of common mail prefixes and extra spacing, so
`Re: FH VFD Signup` will still be accepted.
The fetcher writes `players.csv` and `players_email.csv` into the matching
game's data directory.

1. Prepare signups CSV (`email,species,home_planet,gov_name,gov_type,ML,GV,LS,BI`).
2. Create game:

```bash
python3 ../../tools/game_setup.py < signups.csv
```

3. Create maps:

```bash
python3 ../../tools/create_map.py
```

4. Optional: inject intro text into current reports:

```bash
python3 ../../tools/turn_inject.py < ../../doc/intro.txt
```

5. Build first-turn player packets:

```bash
python3 ../../tools/game_packet.py
```

6. Send turn packets:

```bash
python3 ../../tools/turn_send.py
```

The setup tools now produce these files during the first-turn workflow:

- `galaxy.map.pdf` and `galaxy.map.txt`
- `spNN.rpt.t1.txt`
- `spNN.zip` packet files containing the report, map files, and policies document if found

`game_packet.py` looks for policies in `game_policies.pdf` first, then `gameDocs/policies.txt`.

### 5.2 Run each turn

1. Collect orders into `spNN.ord` files.
2. Optional cleanup of order file formatting:

```bash
python3 ../../tools/orders_clean.py
```

3. Run turn simulation in temporary directory:

```bash
python3 ../../tools/turn_run.py
```

4. If needed, rerun from scratch:

```bash
python3 ../../tools/turn_run.py --discard
```

5. Review results in the reported temp directory.
6. Commit tested turn to live data:

```bash
python3 ../../tools/turn_confirm.py
```

7. Archive and cleanup turn artifacts:

```bash
python3 ../../tools/turn_save.py
```

8. Send reports:

```bash
python3 ../../tools/turn_send.py
```

## 6. Turn Processing Pipeline (Engine Binaries)

The normal turn order is:

1. `NoOrders` (skip on turn 1)
2. `Combat`
3. `PreDeparture`
4. `Jump`
5. `Production`
6. `PostArrival`
7. `Locations`
8. `Strike`
9. `Finish`
10. `Report`

This is the same sequence documented in `doc/gm_sequence` and implemented by `tools/turn_run.py`.

## 7. Python Tool Command Reference

### Game setup and packaging

- `game_setup.py`: create galaxy, assign homes, add species, run first `Finish`/`Report`, then rename first-turn reports to `spNN.rpt.t1.txt`.
- `create_map.py`: generate `galaxy_map_3d.pdf`, `galaxy.map.pdf`, combined `galaxy.map.pdf`, and `galaxy.map.txt`.
- `game_packet.py`: create first-turn zip packets (`spNN.zip`) from the `.txt` report files plus map/policies files.
- `game_setup_jm.py`: alternate setup variant.

### Turn operation

- `turn_run.py`: run full pipeline in temporary test directory.
  - flags: `-c/--config`, `-d/--discard`
- `turn_confirm.py`: copy tested results from temp to data directory.
  - flags: `-c/--config`
- `turn_save.py`: move/archive reports/orders, save stats, cleanup logs.
  - flags: `-c/--config`
- `turn_send.py`: email turn results (or game-start packets).
  - flags: `-c/--config`, `-t/--test`, `-s/--species`, `-f/--file`, `-u/--subject`
- `turn_reminder.py`: email reminder to players with missing `.ord` files.
  - flags: `-c/--config`, `-t/--test`, `-s/--species`
- `turn_inject.py`: prepend message text from stdin to turn reports.
  - flags: `-c/--config`, `-t/--test`

### Orders intake and validation

- `orders_fetch.py`: read unread IMAP messages, extract orders, save `spNN.ord`, send receipt.
- `orders_clean.py`: remove blank lines from order files.
- `orders_status.py`: verify orders and print status per species; optional email notification.
  - flags: `-c/--config`, `-t/--test`, `-s/--species`, `-e/--email`

### Signup utilities (legacy Google integration)

- `signups_verify.py`: validates `players.csv` and appends approved rows into the game's signup CSV file when the email is not already present.
- `signups_fetch.py`: reads structured signup emails and writes `players.csv` plus `players_email.csv`.

Note: `signups_fetch.py` pulls mailbox signups into `players.csv` and `players_email.csv`, then `signups_verify.py` uses `players_email.csv` as a species-to-email fallback while appending only new signup rows into the game CSV.

## 8. Legacy Shell/Perl Workflow (bash/)

These scripts are older but still useful references.

- `fhtest` (must be sourced): run turn pipeline in `/tmp/fhtest.dir`
  - usage: `source fhtest`
- `fhsave` (must be sourced): copy tested outputs back from `/tmp/fhtest.dir`
  - usage: `source fhsave`
- `fhclean`: archive `.dat`, move `.ord`/reports, generate `Stats`, cleanup temp files
- `fhreports`: mail reports listed in `fh_names`
- `fhorders`: parse mailbox and generate `spNN.ord`
- `fhmail <file> <subject>`: mail an arbitrary file to all players
- `orders.pl`: order syntax validator (reads from stdin)
- `strip.pl`: extract plain text MIME body from email on stdin
- `Auto.pl`: old automated game setup tool
- `fhmake_packet`, `create_map.sh`, `fhprocmail`: legacy site-specific scripts with hardcoded paths

## 9. Engine Command Reference (`bin/`)

### Primary gameplay executables

- `NewGalaxy`: generate galaxy and base data files
- `MakeHomes`: generate candidate home systems
- `HomeSystem`, `HomeSystemAuto`: choose/assign home systems
- `AddSpecies`, `AddSpeciesAuto`: add species and initialize species data
- `NoOrders`: create default behavior for players with no orders
- `Combat`, `Strike`: combat phases
- `PreDeparture`, `Jump`, `PostArrival`: movement phases
- `Production`: production/research phase
- `Locations`: rebuild species location tracking
- `Finish`: final accounting and end-of-turn updates
- `Report`: generate per-species reports
- `Report`: generate per-species reports (`spNN.rpt.tT` in the temp run, renamed to `spNN.rpt.tT.txt` in the data directory)
- `TurnNumber`: print current turn number
- `Stats`: output game statistics

### Utility executables

- `ListGalaxy`, `MapGalaxy`, `PrintMap`, `ShowGalaxy`, `Near`, `ScanSpXYZ`
- `Edit`, `Set`
- `AsciiToBinary`, `BinaryToAscii`

## 10. Player Orders File Structure

Orders are grouped by sections and validated by `bash/orders.pl`.

Expected section markers:

- `START COMBAT` ... `END`
- `START PRE-DEPARTURE` ... `END`
- `START JUMPS` ... `END`
- `START PRODUCTION` ... `END`
- `START POST-ARRIVAL` ... `END`
- `START STRIKE` ... `END`

Only one instance of each section should appear.

## 11. Player Order Commands (Abbreviation Reference)

From `src/fh.h` command table:

- `ALL` Ally
- `AMB` Ambush
- `ATT` Attack
- `AUT` Auto
- `BAS` Base
- `BAT` Battle
- `BUI` Build
- `CON` Continue
- `DEE` Deep
- `DES` Destroy
- `DEV` Develop
- `DIS` Disband
- `END` End
- `ENE` Enemy
- `ENG` Engage
- `EST` Estimate
- `HAV` Haven
- `HID` Hide
- `HIJ` Hijack
- `IBU` Ibuild
- `ICO` Icontinue
- `INS` Install
- `INT` Intercept
- `JUM` Jump
- `LAN` Land
- `MES` Message
- `MOV` Move
- `NAM` Name
- `NEU` Neutral
- `ORB` Orbit
- `PJU` Pjump
- `PRO` Production
- `REC` Recycle
- `REP` Repair
- `RES` Research
- `SCA` Scan
- `SEN` Send
- `SHI` Shipyard
- `STA` Start
- `SUM` Summary
- `SUR` Surrender
- `TAR` Target
- `TEA` Teach
- `TEC` Tech
- `TEL` Telescope
- `TER` Terraform
- `TRA` Transfer
- `UNL` Unload
- `UPG` Upgrade
- `VIS` Visited
- `WIT` Withdraw
- `WOR` Wormhole
- `ZZZ`

For full syntax examples and game rules, see `doc/rules` and generated manual in `doc/manual/`.

## 12. Typical Directory Layout For A Running Game

Inside a game data directory after several turns:

- live state: `*.dat`
- incoming orders: `spNN.ord`
- current turn output: `spNN.rpt.tT.txt`
- archive: `backup/turnT/`
- report archive: `reports/` and `reports/stats/`

## 13. Troubleshooting

- `interspecies.dat present. Have you forgotten to fhclean?`
  - Run archive/cleanup (`turn_save.py`) and remove stale turn artifacts.

- `Temp directory exists ... Maybe you need --discard?`
  - Use `turn_run.py --discard` if you intentionally want to rerun.

- Missing map merge tool
  - Install `pdftk` or `pdfunite`.

- Email scripts not working
  - Verify credentials and provider policy.
  - Some scripts contain hardcoded paths from prior deployments and must be edited for your environment.

## 14. Minimal Quick Start

From repository root:

```bash
cd src && ./make.all
cd ../games/NEB
python3 ../../tools/game_setup.py < signups.csv
python3 ../../tools/create_map.py
python3 ../../tools/game_packet.py
```

Each turn:

```bash
python3 ../../tools/orders_clean.py
python3 ../../tools/turn_run.py
python3 ../../tools/turn_confirm.py
python3 ../../tools/turn_save.py
python3 ../../tools/turn_send.py
```
