#!/usr/bin/env python3
"""
Validate `players.csv` and copy the approved rows into the game's signup CSV.

This is the final step after `signups_fetch.py` has pulled structured signup
emails into `players.csv`.

For the game configured in `farhorizons.yml`, this script will:

1. Read `players.csv` from the game's data directory.
2. Validate each row against the standard Far Horizons signup format.
3. Write the validated rows into the game's signup CSV file.

For VFD, that target file is `vallenfield.csv`.
"""

from __future__ import annotations

import csv
import getopt
import os
import re
import sys
from pathlib import Path

import fhutils


def validate_signup_row(row, row_index):
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
        if len(value) > 128:
            raise ValueError(
                "CSV row %d: field '%s' exceeds 128 chars (%d): %s"
                % (row_index, label, len(value), value)
            )

    if email and len(email) > 80:
        raise ValueError("CSV row %d: field 'email' exceeds 80 chars: %s" % (row_index, email))

    for label, value in [("ML", ML), ("GV", GV), ("LS", LS), ("BI", BI)]:
        if not value.isdigit():
            raise ValueError("CSV row %d: field '%s' must be an integer: %s" % (row_index, label, value))

    tech_total = sum(int(v) for v in (ML, GV, LS, BI))
    if tech_total != 15:
        raise ValueError("CSV row %d: tech totals must add up to 15 (got %d)" % (row_index, tech_total))

    return [email, sp_name, home_planet, gov_name, gov_type, ML, GV, LS, BI]


def _normalize_email_address(value: str) -> str:
    candidates = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value or "")
    if candidates:
        return candidates[0].strip().lower()
    return value.strip().lower()


def validate_players_email_row(row, row_index):
    if len(row) != 2:
        raise ValueError("CSV row %d in players_email.csv must have 2 fields: species,email" % row_index)

    species, email = [x.strip() for x in row]
    if row_index == 1 and species.lower() in ("name", "species") and email.lower() in ("email", "email address"):
        return None
    if not species:
        raise ValueError("CSV row %d in players_email.csv: species cannot be empty" % row_index)
    if not email:
        raise ValueError("CSV row %d in players_email.csv: email cannot be empty" % row_index)
    if len(species) > 128:
        raise ValueError("CSV row %d in players_email.csv: species exceeds 128 chars: %s" % (row_index, species))
    return species, _normalize_email_address(email)


def _game_csv_name(game_name: str) -> str:
    return "%s.csv" % game_name.replace(" ", "").lower()


def _read_players_email_map(players_email_csv: Path) -> dict[str, str]:
    email_map: dict[str, str] = {}
    if not players_email_csv.exists():
        return email_map

    with players_email_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader, start=1):
            if not row or all(not cell.strip() for cell in row):
                continue
            parsed = validate_players_email_row(row, idx)
            if parsed is None:
                continue
            species, email = parsed
            email_map[species] = email
    return email_map


def _read_existing_rows(target_csv: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    if not target_csv.exists():
        return rows

    with target_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            rows.append([cell.strip() for cell in row])
    return rows


def main(argv=None):
    config_file = None
    if argv is None:
        argv = sys.argv[1:]

    try:
        opts, _args = getopt.getopt(argv, "hc:", ["help", "config="])
    except Exception:
        print(__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif opt in ("-c", "--config"):
            config_file = arg

    config = fhutils.GameConfig(config_file) if config_file else fhutils.GameConfig()
    game = config.gameslist[0]
    game_name = game["name"]
    data_dir = Path(game["datadir"])
    players_csv = data_dir / "players.csv"
    players_email_csv = data_dir / "players_email.csv"
    target_csv = data_dir / _game_csv_name(game_name)

    if not players_csv.exists():
        print("players.csv not found: %s" % players_csv)
        sys.exit(2)

    rows = []
    errors = []
    email_map = _read_players_email_map(players_email_csv)
    existing_rows = _read_existing_rows(target_csv)
    existing_emails = set()

    for row in existing_rows:
        if len(row) >= 1:
            existing_emails.add(_normalize_email_address(row[0]))

    with players_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader, start=1):
            if not row or all(not cell.strip() for cell in row):
                continue
            try:
                validated = validate_signup_row(row, idx)
                validated_email = _normalize_email_address(validated[0])
                fallback_email = email_map.get(validated[1])
                if validated_email and "@" in validated_email:
                    validated[0] = validated_email
                elif fallback_email:
                    validated[0] = fallback_email
                else:
                    raise ValueError(
                        "CSV row %d: missing or invalid email and no players_email.csv entry for species '%s'"
                        % (idx, validated[1])
                    )

                final_email = _normalize_email_address(validated[0])
                if final_email in existing_emails:
                    print(
                        "Skipping duplicate signup email already present in %s: %s"
                        % (target_csv, final_email)
                    )
                    continue

                existing_emails.add(final_email)
                validated[0] = final_email
                rows.append(validated)
            except ValueError as exc:
                errors.append(str(exc))

    if errors:
        print("Signup CSV validation failed:")
        for err in errors:
            print("  - %s" % err)
        sys.exit(1)

    data_dir.mkdir(parents=True, exist_ok=True)
    combined_rows = existing_rows + rows
    tmp_path = target_csv.with_suffix(target_csv.suffix + ".tmp")
    with tmp_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(combined_rows)

    os.replace(tmp_path, target_csv)
    print("Validated %d new signup row(s) from %s" % (len(rows), players_csv))
    print("Wrote %s" % target_csv)


if __name__ == "__main__":
    main()