# Far Horizons Quick Ops Cheat Sheet

Fast, practical commands for day-to-day Game Master operations.

## 0) Where to run commands

- Build commands: repository root
- Game commands: your game data directory (example: `games/NEB`)

## 1) One-time setup

From repo root:

```bash
cd src
./make.all
python3 -m pip install -r ../tools/pyrequirements.txt
```

## 2) New game (first turn)

From game data directory (example: `games/NEB`):

```bash
python3 ../../tools/game_setup.py < signups.csv
python3 ../../tools/create_map.py
python3 ../../tools/game_packet.py
python3 ../../tools/turn_send.py
```

Optional intro injection before sending:

```bash
python3 ../../tools/turn_inject.py < ../../doc/intro.txt
```

The GUI also includes a **New Game Wizard** that runs the same first-turn sequence interactively.

Notes:

- `game_setup.py` writes first-turn reports as `spNN.rpt.t1.txt`
- `create_map.py` writes both `galaxy.map.pdf` and `galaxy.map.txt`
- `game_packet.py` bundles the `.txt` reports plus map/policies files, and will also look in `gameDocs/policies.txt`

## 3) Standard turn cycle (most used)

From game data directory:

```bash
python3 ../../tools/orders_clean.py
python3 ../../tools/turn_run.py
python3 ../../tools/turn_confirm.py
python3 ../../tools/turn_save.py
python3 ../../tools/turn_send.py
```

## 4) If something goes wrong

Rerun turn processing from scratch (discard old temp run):

```bash
python3 ../../tools/turn_run.py --discard
```

Check order quality/status:

```bash
python3 ../../tools/orders_status.py
```

Test email output without sending:

```bash
python3 ../../tools/turn_send.py --test
python3 ../../tools/turn_reminder.py --test
```

## 5) Daily intake shortcuts

Fetch new orders from mail:

```bash
python3 ../../tools/orders_fetch.py
```

Remind only players missing orders:

```bash
python3 ../../tools/turn_reminder.py
```

## 6) High-value options

Most tools:

```bash
-h, --help
-c, --config <file>
```

Commonly used extras:

- `turn_run.py`: `--discard`
- `turn_send.py`: `--test`, `--species <NN>`, `--file <path>`, `--subject <text>`
- `turn_reminder.py`: `--test`, `--species <NN>`
- `turn_inject.py`: `--test`
- `orders_status.py`: `--species <NN>`, `--email`

## 7) Turn pipeline (engine order)

When `turn_run.py` executes, the engine sequence is:

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

## 8) Key files to watch

In your game data directory:

- `spNN.ord`: incoming orders
- `spNN.rpt.tT.txt`: output reports
- `galaxy.map.pdf` / `galaxy.map.txt`: generated galaxy maps
- `fh_names`: species/email map
- `backup/turnT/`: archived state/orders
- `reports/`: archived reports
- `reports/stats/stats.tT`: turn stats

## 9) Minimal “happy path” checklist

1. Orders in place (`spNN.ord` files).
2. Run `turn_run.py` and review output/temp dir.
3. Run `turn_confirm.py`.
4. Run `turn_save.py`.
5. Run `turn_send.py`.

## 10) Pointers

- Full manual: `doc/USER_MANUAL.md`
- Tool details: `tools/README.md`
- Core rules: `doc/rules`
