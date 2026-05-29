#!/usr/bin/env python3
"""
 Utility to read player registrations from signup emails and save them in
 players.csv.

 Each signup email should use a labeled plain-text template like:

     Email: player@example.com
     Species: Vallen
     Home Planet: Vallen Prime
     Government Name: The Concord
     Government Type: Democratic Republic
     ML: 5
     GV: 4
     LS: 3
     BI: 3

 The script reads unread signup mail from the configured mailbox, validates the
 required fields, and writes:

 - players.csv: email, species, home_planet, gov_name, gov_type, ML, GV, LS, BI
 - players_email.csv: species, email

 These files can then be used for game setup and mail distribution.

 Use a subject line that contains "FH <game stub> Signup" to mark signup emails,
 for example "FH GA Signup".
"""

import csv
import email.utils
import os
import re
import sys

from imapclient import IMAPClient

try:
    import pyzmail36 as pyzmail
except ImportError:
    import pyzmail

import fhutils


FIELD_PATTERNS = {
    "email": re.compile(r"(?im)^\s*Email\s*:\s*(.+?)\s*$"),
    "species": re.compile(r"(?im)^\s*Species\s*:\s*(.+?)\s*$"),
    "home_planet": re.compile(r"(?im)^\s*Home\s*Planet\s*:\s*(.+?)\s*$"),
    "gov_name": re.compile(r"(?im)^\s*Government\s*Name\s*:\s*(.+?)\s*$"),
    "gov_type": re.compile(r"(?im)^\s*Government\s*Type\s*:\s*(.+?)\s*$"),
    "ML": re.compile(r"(?im)^\s*ML\s*:\s*(.+?)\s*$"),
    "GV": re.compile(r"(?im)^\s*GV\s*:\s*(.+?)\s*$"),
    "LS": re.compile(r"(?im)^\s*LS\s*:\s*(.+?)\s*$"),
    "BI": re.compile(r"(?im)^\s*BI\s*:\s*(.+?)\s*$"),
}

def _check_length(value):
    return 7 <= len(value) <= 128


def _normalize_email_address(value):
    candidates = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value or "")
    if candidates:
        return candidates[0].strip().lower()
    parsed = email.utils.parseaddr(value or "")[1].strip().lower()
    return parsed


def _extract_plain_text(mail):
    if mail.is_multipart():
        for part in mail.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_type() != "text/plain":
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    else:
        payload = mail.get_payload(decode=True)
        if payload is not None:
            charset = mail.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        payload = mail.get_payload()
        if isinstance(payload, str):
            return payload
    return ""


def _parse_signup_text(text, from_address=""):
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    fields = {}

    for key, pattern in FIELD_PATTERNS.items():
        match = pattern.search(normalized)
        if match:
            fields[key] = match.group(1).strip()

    if not fields:
        return None, ["No signup template fields found in message body."]

    errors = []
    required = ["species", "home_planet", "gov_name", "gov_type", "ML", "GV", "LS", "BI"]
    for key in required:
        if key not in fields or not fields[key]:
            errors.append("Missing required field: %s" % key)

    email_value = _normalize_email_address(fields.get("email", from_address))
    if not email_value:
        errors.append("Missing email address in body and From header.")

    from_address = _normalize_email_address(from_address)

    for key in ["species", "home_planet", "gov_name", "gov_type"]:
        value = fields.get(key, "").strip()
        if value and not _check_length(value):
            errors.append("%s must be between 7 and 128 characters." % key.replace("_", " ").title())

    tech_total = 0
    for key in ["ML", "GV", "LS", "BI"]:
        value = fields.get(key, "").strip()
        try:
            tech_total += int(value)
        except ValueError:
            errors.append("%s must be an integer." % key)

    if not errors and tech_total != 15:
        errors.append("The total number of tech points must equal 15.")

    if errors:
        return None, errors

    return [
        email_value,
        fields["species"],
        fields["home_planet"],
        fields["gov_name"],
        fields["gov_type"],
        fields["ML"],
        fields["GV"],
        fields["LS"],
        fields["BI"],
    ], []


def _subject_matches_stub(subject, stub):
    normalized_subject = re.sub(r"\s+", " ", subject or "").strip().lower()
    normalized_stub = re.escape(str(stub or "").strip().lower())
    if not normalized_stub:
        return False
    pattern = r"\bfh\s+%s\s+signup\b" % normalized_stub
    return re.search(pattern, normalized_subject) is not None


def _read_config():
    config = fhutils.GameConfig()
    account = config.config.get("googleaccount", {})
    user = account.get("user")
    password = account.get("password")
    if not user or not password:
        raise RuntimeError("googleaccount.user and googleaccount.password must be set in farhorizons.yml")
    games_by_stub = {}
    for game in config.gameslist:
        stub = str(game.get("stub", "")).strip().lower()
        if stub:
            games_by_stub[stub] = game
    return config, user, password, games_by_stub


def main():
    _config, user_name, user_pass, games_by_stub = _read_config()

    player_rows_by_game = {}
    email_rows_by_game = {}

    server = IMAPClient("imap.gmail.com", ssl=True)
    server.login(user_name, user_pass)
    server.select_folder("INBOX", readonly=True)
    unread_list = server.search(["UNSEEN"])

    if not unread_list:
        print("No unread signup emails found.")

    for unread in unread_list:
        raw_messages = server.fetch([unread], [b"BODY[]", "FLAGS"])
        mail = pyzmail.PyzMessage.factory(raw_messages[unread][b"BODY[]"])
        addressor = mail.get("From") or ""
        from_address = email.utils.parseaddr(addressor)[1].strip().lower()
        subject = mail.get_subject() or ""

        matched_game = None
        matched_stub = None
        for stub, game in games_by_stub.items():
            if _subject_matches_stub(subject, stub):
                matched_game = game
                matched_stub = stub
                break

        if matched_game is None:
            print("Skipping non-signup message from %s [%s]" % (from_address or "unknown", subject))
            continue

        text = _extract_plain_text(mail)
        parsed_row, errors = _parse_signup_text(text, from_address=from_address)

        if parsed_row is None:
            print("Skipping message from %s [%s]" % (from_address or "unknown", subject))
            for error in errors:
                print("  - %s" % error)
            continue

        game_dir = matched_game["datadir"]
        player_rows = player_rows_by_game.setdefault(game_dir, [])
        email_rows = email_rows_by_game.setdefault(game_dir, ["Name, Email Address\n"])
        player_rows.append(parsed_row)
        email_rows.append("%s,%s\n" % (parsed_row[1], parsed_row[0]))
        print("Parsed signup for %s (%s) into game stub %s" % (parsed_row[1], parsed_row[0], matched_stub.upper()))

    for game_dir, player_rows in player_rows_by_game.items():
        email_rows = email_rows_by_game.get(game_dir, ["Name, Email Address\n"])
        os.makedirs(game_dir, exist_ok=True)
        player_csv_path = os.path.join(game_dir, "players.csv")
        email_csv_path = os.path.join(game_dir, "players_email.csv")

        with open(player_csv_path, "w", newline="", encoding="utf-8") as player_csv:
            writer = csv.writer(player_csv)
            writer.writerows(player_rows)

        with open(email_csv_path, "w", newline="", encoding="utf-8") as email_csv:
            email_csv.writelines(email_rows)

        print("Wrote %d signup row(s) to %s" % (len(player_rows), player_csv_path))

    if not player_rows_by_game:
        print("No matching signup emails were parsed.")

if __name__ == "__main__":
    main()
