import re, os, string, sys, subprocess, itertools, shutil
import smtplib
import mimetypes
import yaml
from dateutil import rrule
from dateutil.parser import parse
from dateutil import tz
import dateutil
import datetime

def _is_elf(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def _to_wsl_path(path):
    norm = os.path.abspath(path).replace("\\", "/")
    if len(norm) >= 3 and norm[1] == ":" and norm[2] == "/":
        drive = norm[0].lower()
        rest = norm[3:]
        return "/mnt/%s/%s" % (drive, rest)
    return norm


def _looks_like_windows_path(value):
    if not isinstance(value, str):
        return False
    return len(value) >= 3 and value[1] == ":" and (value[2] == "\\" or value[2] == "/")


def _to_wsl_arg(value):
    if _looks_like_windows_path(value):
        return _to_wsl_path(value)
    return value


def run(bindir, tool, args = []):
    tool_path = os.path.join(bindir, tool)
    cmd_args = list(args) if args else []

    def _run_checked(cmd):
        completed = subprocess.run(cmd, text=True, encoding="utf-8", capture_output=True)
        if completed.returncode != 0:
            print("ERROR: command failed:")
            print("  " + " ".join(cmd))
            if completed.stdout:
                print("--- stdout ---")
                print(completed.stdout)
            if completed.stderr:
                print("--- stderr ---")
                print(completed.stderr)
            err_text = (completed.stdout or "") + "\n" + (completed.stderr or "")
            if "has no installed distributions" in err_text:
                print("WSL is installed but no Linux distribution is configured.")
                print("Run: wsl --install -d Ubuntu")
                print("Then re-run the GUI action.")
            if os.name == "nt" and "cannot execute: required file not found" in err_text:
                print("The selected engine binary appears to require an unavailable Linux loader (often old ELF32).")
                print("Rebuild that binary in WSL as x86_64, or install 32-bit compatibility libs in WSL.")
                print("For this repo, run: wsl bash -lc 'cd /mnt/c/Users/ltanh/Documents/Far-Horizons/src && ./build_required_wsl.sh'")
            sys.exit(1)
        return completed.stdout

    try:
        # Native path for non-Windows hosts.
        if os.name != "nt":
            return _run_checked([tool_path] + cmd_args)

        # On Windows, prefer a native .exe if available.
        exe_path = tool_path + ".exe"
        if os.path.exists(exe_path):
            return _run_checked([exe_path] + cmd_args)

        # If the binary is Linux ELF (or a symlink that Windows cannot directly access), run through WSL.
        is_inaccessible_link = os.path.lexists(tool_path) and not os.path.exists(tool_path)
        if _is_elf(tool_path) or is_inaccessible_link:
            wsl = shutil.which("wsl")
            if not wsl:
                print("ERROR: '%s' is a Linux ELF binary and cannot run natively on Windows." % tool_path)
                print("Install WSL or provide Windows-compiled .exe binaries in bindir.")
                sys.exit(1)

            wsl_cmd = [
                wsl,
                "--cd",
                _to_wsl_path(os.getcwd()),
                _to_wsl_path(tool_path),
            ] + [_to_wsl_arg(arg) for arg in cmd_args]
            return _run_checked(wsl_cmd)

        # Final fallback: attempt direct execution and let OS errors surface.
        return _run_checked([tool_path] + cmd_args)

    except OSError as exc:
        print("ERROR: failed to execute tool '%s' from '%s'" % (tool, bindir))
        print(str(exc))
        if os.name == "nt":
            print("Hint: If binaries are Linux ELF, install/use WSL or rebuild binaries as .exe.")
        sys.exit(1)

def natatime(itr, fillvalue=None, n=2):
    """
    get values from an iterator n at a time
    http://stackoverflow.com/questions/1528711/reading-lines-2-at-a-time/1528769#1528769
    """
    return itertools.zip_longest(*(iter(itr),)*n, fillvalue=fillvalue)

class GameConfig(object):

    def __init__(self, config_file="farhorizons.yml"):
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            self.user = self.config['googleaccount']['user']
            self.doc_name = self.config['googleaccount']['spreadsheet']
            self.password = self.config['googleaccount']['password']

            self.bindir = self.config['bindir']
            self.gameslist = []
            for game in self.config['games']:
                d = dict()
                d['name'] = game
                d['stub'] = self.config[game]['stub']
                d['datadir'] = self.config[game]['datadir']
                d['timezone'] = self.config[game]['timezone']
                add_default_tz = lambda x, tzinfo: x.replace(tzinfo=x.tzinfo or tzinfo)
                zone = tz.gettz(d['timezone'])
                d['zone'] = zone
                do_parse = lambda x: add_default_tz(parse(x), zone)

                weekdays = tuple([do_parse(x).weekday() for x in self.config[game]['deadlines']])
                hours = tuple([do_parse(x).hour for x in self.config[game]['deadlines']])
                minutes = tuple([do_parse(x).minute for x in self.config[game]['deadlines']])
                d['deadline'] = rrule.rrule(rrule.WEEKLY, byweekday=weekdays,byhour=hours,byminute=minutes,dtstart=datetime.datetime.now(zone))

                if 'tmpdir' in self.config[game]:
                    d['tmpdir'] = self.config[game]['tmpdir']
                self.gameslist.append( d )


        except yaml.YAMLError as exc:
            print("Error parsing %s file" % (self.config_file))
            print(exc)
            sys.exit(1)

    def registrations(self):
        """Return registrations from the spreadsheet"""
        pass

    def save(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def write_tmpdir(self, game, tmpdir):
        """
        Saves the tmpdir as a value under game.
        """
        if not game in self.config:
            return
        self.config[game]['tmpdir'] = tmpdir
        self.save()

class Game(object):
    def __init__(self):
        self.players = []
        with open('fh_names') as f:
            for num,name,email in natatime(f,'',3):
                self.players.append({'num':num.strip(), 'name':name.strip(), 'email':email.strip().lower()})
