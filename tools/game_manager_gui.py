#!/usr/bin/env python3
"""
Far Horizons Game Manager GUI

A FreeSimpleGUI-based control panel for Far Horizons game operations.
It can run all primary GM automation tools and browse/view game files.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import ctypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
import fhutils

try:
    import FreeSimpleGUI as sg
except ImportError:
    print("FreeSimpleGUI is not installed. Install dependencies with:")
    print("python3 -m pip install -r pyrequirements.txt")
    raise


SCRIPT_DIR = Path(__file__).resolve().parent

THEME_OPTIONS = [
    "FH Light Classic",
    "FH Light Sky",
    "FH Light Sand",
    "FH Light Mint",
    "FH Dark Slate",
    "FH Dark Ocean",
    "FH Dark Ember",
    "FH Dark Matrix",
]

THEME_DEFINITIONS = {
    "FH Light Classic": {
        "BACKGROUND": "#f4f6f8",
        "TEXT": "#1f2328",
        "INPUT": "#ffffff",
        "TEXT_INPUT": "#1f2328",
        "SCROLL": "#8b949e",
        "BUTTON": ("#ffffff", "#2d5b88"),
        "PROGRESS": ("#2d5b88", "#d9e2ec"),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    },
    "FH Light Sky": {
        "BACKGROUND": "#eaf4ff",
        "TEXT": "#11263a",
        "INPUT": "#ffffff",
        "TEXT_INPUT": "#11263a",
        "SCROLL": "#5e7b99",
        "BUTTON": ("#ffffff", "#3a76b3"),
        "PROGRESS": ("#3a76b3", "#cfe5fb"),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    },
    "FH Light Sand": {
        "BACKGROUND": "#fbf5e9",
        "TEXT": "#3a2f1b",
        "INPUT": "#fffdf7",
        "TEXT_INPUT": "#3a2f1b",
        "SCROLL": "#7f6a45",
        "BUTTON": ("#ffffff", "#a87a2f"),
        "PROGRESS": ("#a87a2f", "#eadcc2"),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    },
    "FH Light Mint": {
        "BACKGROUND": "#ecf8f3",
        "TEXT": "#113128",
        "INPUT": "#ffffff",
        "TEXT_INPUT": "#113128",
        "SCROLL": "#4f7b6d",
        "BUTTON": ("#ffffff", "#2f8b6e"),
        "PROGRESS": ("#2f8b6e", "#cfe8df"),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    },
    "FH Dark Slate": {
        "BACKGROUND": "#1c2128",
        "TEXT": "#e6edf3",
        "INPUT": "#262c36",
        "TEXT_INPUT": "#e6edf3",
        "SCROLL": "#73808c",
        "BUTTON": ("#f0f6fc", "#3d6ea8"),
        "PROGRESS": ("#3d6ea8", "#11161d"),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    },
    "FH Dark Ocean": {
        "BACKGROUND": "#101b26",
        "TEXT": "#d7e6f5",
        "INPUT": "#142435",
        "TEXT_INPUT": "#d7e6f5",
        "SCROLL": "#5f7e99",
        "BUTTON": ("#f4f9ff", "#2d7cb8"),
        "PROGRESS": ("#2d7cb8", "#0b1219"),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    },
    "FH Dark Ember": {
        "BACKGROUND": "#241a17",
        "TEXT": "#f2e5dc",
        "INPUT": "#2e211d",
        "TEXT_INPUT": "#f2e5dc",
        "SCROLL": "#98796d",
        "BUTTON": ("#fff4ef", "#b85c2d"),
        "PROGRESS": ("#b85c2d", "#16100e"),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    },
    "FH Dark Matrix": {
        "BACKGROUND": "#08120b",
        "TEXT": "#78ff9f",
        "INPUT": "#0d1e13",
        "TEXT_INPUT": "#a7ffbf",
        "SCROLL": "#3ea65f",
        "BUTTON": ("#0a1a10", "#2fdc67"),
        "PROGRESS": ("#2fdc67", "#030804"),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    },
}

DEFAULT_THEME = "FH Light Classic"
GUI_SETTINGS_PATH = SCRIPT_DIR / ".fh_gui_settings.json"


def register_themes() -> None:
    for theme_name, theme_def in THEME_DEFINITIONS.items():
        if hasattr(sg, "theme_add_new"):
            sg.theme_add_new(theme_name, theme_def)
        elif hasattr(sg, "LOOK_AND_FEEL_TABLE"):
            sg.LOOK_AND_FEEL_TABLE[theme_name] = theme_def


def get_work_area_rect() -> tuple[int, int, int, int]:
    """Return usable desktop rectangle as (left, top, right, bottom).

    On Windows this excludes the taskbar via SPI_GETWORKAREA. Other platforms
    fall back to full screen size from Tk with origin at (0, 0).
    """
    if sys.platform.startswith("win"):
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        rect = RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)

    width, height = sg.Window.get_screen_size()
    return 0, 0, max(1, int(width)), max(1, int(height))


def clamp_window_to_work_area(window: sg.Window, desired_size: tuple[int, int], padding: int = 24) -> None:
    left, top, right, bottom = get_work_area_rect()
    work_w = max(1, right - left)
    work_h = max(1, bottom - top)
    desired_w, desired_h = desired_size
    width = max(700, min(desired_w, work_w - padding))
    height = max(520, min(desired_h, work_h - padding))
    window.set_size((width, height))

    # Start centered within the usable area (respecting monitor/work-area offset).
    x = left + max(0, (work_w - width) // 2)
    y = top + max(0, (work_h - height) // 2)
    window.move(x, y)

    # Decorations/title bars can make the outer bounds larger than requested size,
    # so clamp a second time using actual window geometry.
    window.TKroot.update_idletasks()
    actual_w = int(window.TKroot.winfo_width())
    actual_h = int(window.TKroot.winfo_height())
    clamped_x = min(max(x, left), max(left, right - actual_w))
    clamped_y = min(max(y, top), max(top, bottom - actual_h))
    if clamped_x != x or clamped_y != y:
        window.move(clamped_x, clamped_y)


def place_window_in_work_area(window: sg.Window, padding: int = 24) -> None:
    """Center an already-sized window and clamp it inside the visible work area."""
    left, top, right, bottom = get_work_area_rect()
    work_w = max(1, right - left)
    work_h = max(1, bottom - top)

    window.TKroot.update_idletasks()
    actual_w = int(window.TKroot.winfo_width())
    actual_h = int(window.TKroot.winfo_height())

    x = left + max(0, (work_w - actual_w) // 2)
    y = top + max(0, (work_h - actual_h) // 2)
    x = min(max(x, left + padding // 2), max(left + padding // 2, right - actual_w - padding // 2))
    y = min(max(y, top + padding // 2), max(top + padding // 2, bottom - actual_h - padding // 2))
    window.move(x, y)


def load_saved_theme() -> str:
    try:
        if not GUI_SETTINGS_PATH.exists():
            return DEFAULT_THEME
        data = json.loads(GUI_SETTINGS_PATH.read_text(encoding="utf-8"))
        theme = data.get("theme")
        if theme in THEME_OPTIONS:
            return theme
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return DEFAULT_THEME


def save_theme(theme_name: str) -> None:
    if theme_name not in THEME_OPTIONS:
        return
    data = {"theme": theme_name}
    try:
        if GUI_SETTINGS_PATH.exists():
            current = json.loads(GUI_SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(current, dict):
                current.update(data)
                data = current
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    try:
        GUI_SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def discover_default_config() -> Path:
    candidates = [
        Path.cwd() / "farhorizons.yml",
        SCRIPT_DIR / "farhorizons.yml",
        SCRIPT_DIR.parent / "IncludeTemplates" / "farhorizons.yml",
        SCRIPT_DIR.parent / "IncludeTemplates" / "farhorizons.yml.example",
    ]
    for path in candidates:
        if path.exists():
            return path
    return SCRIPT_DIR.parent / "IncludeTemplates" / "farhorizons.yml.example"


DEFAULT_CONFIG = discover_default_config()


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in {
        ".txt",
        ".log",
        ".ord",
        ".rpt",
        ".msg",
        ".yml",
        ".yaml",
        ".csv",
        ".md",
        ".py",
        ".pl",
        ".sh",
    }


def read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Could not read file: {exc}"


def file_preview(path: Path) -> str:
    if not path.exists():
        return "File does not exist."
    if path.is_dir():
        return f"Directory: {path}"

    stat = path.stat()
    header = [
        f"Path: {path}",
        f"Size: {stat.st_size} bytes",
        f"Modified: {stat.st_mtime}",
        "",
    ]

    if is_text_file(path):
        content = read_text_safely(path)
        return "\n".join(header) + content

    return "\n".join(header) + "Binary or non-text file. Use Open File to inspect externally."


@dataclass
class AppState:
    config_path: Path
    bindir: str = ""
    games: list[str] | None = None
    selected_game: Optional[str] = None
    game_dir: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.games is None:
            self.games = []


class FHGameManagerGUI:
    def __init__(self, theme_name: str = DEFAULT_THEME, config_path: Path | None = None, selected_game: str | None = None) -> None:
        register_themes()
        self.theme_name = theme_name if theme_name in THEME_OPTIONS else DEFAULT_THEME
        self.state = AppState(config_path=DEFAULT_CONFIG)
        if config_path is not None:
            self.state.config_path = config_path
        if selected_game:
            self.state.selected_game = selected_game
        self.player_rows: list[tuple[str, str, str]] = []
        self.window = self._build_window()
        self.window["-CONFIG-"].update(str(self.state.config_path))
        self._load_config(update_ui=False)
        self._sync_ui_from_state()
        self._run_preflight_check(auto=True)

    def _build_window(self) -> sg.Window:
        sg.theme(self.theme_name)

        theme_row = [
            sg.Text("Theme"),
            sg.Combo(THEME_OPTIONS, key="-THEME-", default_value=self.theme_name, readonly=True, size=(22, 1)),
            sg.Button("Apply Theme", key="-APPLY-THEME-"),
        ]

        config_row = [
            sg.Text("Config"),
            sg.Input(str(DEFAULT_CONFIG), key="-CONFIG-", size=(70, 1)),
            sg.FileBrowse(file_types=(("YAML", "*.yml;*.yaml"),)),
            sg.Button("Load Config", key="-LOAD-CONFIG-"),
        ]

        game_row = [
            sg.Text("Game"),
            sg.Combo([], key="-GAME-", readonly=True, size=(40, 1), enable_events=True),
            sg.Text("Game Dir"),
            sg.Input("", key="-GAME-DIR-", size=(50, 1), readonly=True),
            sg.Button("Open Game Dir", key="-OPEN-GAME-DIR-"),
        ]

        preflight_row = [
            sg.Text("Preflight"),
            sg.Text("Not yet run", key="-PREFLIGHT-STATUS-", size=(80, 1), text_color="yellow"),
            sg.Button("Run Preflight", key="-RUN-PREFLIGHT-"),
        ]

        setup_frame = sg.Frame(
            "Setup",
            [
                [
                    sg.Text("Signups CSV"),
                    sg.Input("", key="-SIGNUPS-", size=(40, 1)),
                    sg.FileBrowse(file_types=(("CSV", "*.csv"),)),
                ],
                [
                    sg.Text("Inject Text"),
                    sg.Input("", key="-INJECT-FILE-", size=(40, 1)),
                    sg.FileBrowse(file_types=(("Text", "*.txt;*.md;*.msg"), ("All", "*.*"))),
                ],
                [
                    sg.Button("New Game Wizard", key="-RUN-NEW-GAME-WIZARD-", button_color=("white", "#1a6b2e")),
                    sg.Button("Game Setup", key="-RUN-GAME-SETUP-"),
                    sg.Button("Create Map", key="-RUN-CREATE-MAP-"),
                    sg.Button("Game Packet", key="-RUN-GAME-PACKET-"),
                    sg.Button("Inject Report Text", key="-RUN-TURN-INJECT-"),
                ],
            ],
            expand_x=True,
        )

        orders_frame = sg.Frame(
            "Orders",
            [
                [
                    sg.Button("Fetch Orders", key="-RUN-ORDERS-FETCH-"),
                    sg.Button("Clean Orders", key="-RUN-ORDERS-CLEAN-"),
                    sg.Button("Orders Status", key="-RUN-ORDERS-STATUS-"),
                    sg.Button("Send Reminder", key="-RUN-TURN-REMINDER-"),
                    sg.Button("Order Builder", key="-RUN-ORDER-BUILDER-"),
                ],
                [
                    sg.Text("Species"),
                    sg.Input("", key="-SPECIES-", size=(8, 1)),
                    sg.Checkbox("Test Mode", key="-TEST-MODE-", default=False),
                ],
            ],
            expand_x=True,
        )

        signups_frame = sg.Frame( 
            "Signups",
            [
                [
                    sg.Button("Verify Signups", key="-RUN-SIGNUPS-VERIFY-"),
                    sg.Button("Fetch Signups CSV", key="-RUN-SIGNUPS-FETCH-"),
                    sg.Text("Fetch pulls signup emails into players.csv; Verify appends unique rows into the game CSV."),
                ],
            ],
            expand_x=True,
        )

        turn_frame = sg.Frame(
            "Turn",
            [
                [
                    sg.Button("Run Turn", key="-RUN-TURN-RUN-"),
                    sg.Button("Run Turn (Discard)", key="-RUN-TURN-RUN-DISCARD-"),
                    sg.Button("FH Clean", key="-RUN-TURN-CLEAN-"),
                    sg.Button("Confirm Turn", key="-RUN-TURN-CONFIRM-"),
                    sg.Button("Save Turn", key="-RUN-TURN-SAVE-"),
                    sg.Button("Send Reports", key="-RUN-TURN-SEND-"),
                ]
            ],
            expand_x=True,
        )

        engine_frame = sg.Frame(
            "Engine Binaries",
            [
                [
                    sg.Combo(
                        [
                            "TurnNumber",
                            "ListGalaxy",
                            "Stats",
                            "NoOrders",
                            "Combat",
                            "PreDeparture",
                            "Jump",
                            "Production",
                            "PostArrival",
                            "Locations",
                            "Strike",
                            "Finish",
                            "Report",
                        ],
                        key="-ENGINE-CMD-",
                        default_value="TurnNumber",
                        readonly=True,
                        size=(24, 1),
                    ),
                    sg.Button("Run Engine Command", key="-RUN-ENGINE-CMD-"),
                ]
            ],
            expand_x=True,
        )

        output_tab = sg.Tab(
            "Output",
            [[sg.Multiline("", key="-OUTPUT-", size=(140, 30), autoscroll=True, write_only=True)]],
        )

        files_tab = sg.Tab(
            "Files",
            [
                [
                    sg.Text("Filter"),
                    sg.Input("*", key="-FILE-GLOB-", size=(30, 1), enable_events=True),
                    sg.Button("Refresh Files", key="-REFRESH-FILES-"),
                    sg.Button("Open File", key="-OPEN-FILE-"),
                ],
                [
                    sg.Listbox([], key="-FILE-LIST-", size=(50, 25), enable_events=True),
                    sg.Multiline("", key="-FILE-PREVIEW-", size=(88, 25), autoscroll=False),
                ],
            ],
        )

        player_ops_tab = sg.Tab(
            "Player Ops",
            [
                [
                    sg.Text("Players"),
                    sg.Text("Search"),
                    sg.Input("", key="-PLAYER-SEARCH-", size=(24, 1), enable_events=True),
                    sg.Button("Refresh Players", key="-REFRESH-PLAYERS-"),
                ],
                [
                    sg.Listbox([], key="-PLAYER-LIST-", size=(50, 8), enable_events=True),
                    sg.Multiline("", key="-PLAYER-PREVIEW-", size=(88, 8), autoscroll=False),
                ],
                [
                    sg.Text("Species"),
                    sg.Input("", key="-PLAYER-SPECIES-", size=(8, 1), enable_events=True),
                    sg.Text("Turn"),
                    sg.Combo([], key="-PLAYER-TURN-", size=(12, 1), readonly=False),
                    sg.Button("Refresh Turns", key="-REFRESH-TURNS-"),
                    sg.Checkbox("Test Mode", key="-PLAYER-TEST-MODE-", default=False),
                    sg.Checkbox("Email Errors", key="-PLAYER-EMAIL-ERRORS-", default=False),
                ],
                [
                    sg.Button("Player Orders Status", key="-PLAYER-ORDERS-STATUS-"),
                    sg.Button("Player Reminder", key="-PLAYER-REMINDER-"),
                    sg.Button("Player Send Report", key="-PLAYER-SEND-REPORT-"),
                ],
                [
                    sg.Button("Preview Orders", key="-PLAYER-PREVIEW-ORDERS-"),
                    sg.Button("Preview Latest Report", key="-PLAYER-PREVIEW-REPORT-"),
                    sg.Button("Open Orders", key="-PLAYER-OPEN-ORDERS-"),
                    sg.Button("Open Latest Report", key="-PLAYER-OPEN-REPORT-"),
                    sg.Button("Open In Order Builder", key="-PLAYER-ORDER-BUILDER-"),
                ],
            ],
        )

        layout = [
            theme_row,
            config_row,
            game_row,
            preflight_row,
            [setup_frame],
            [orders_frame],
            [signups_frame],
            [turn_frame],
            [engine_frame],
            [sg.TabGroup([[output_tab, files_tab, player_ops_tab]], expand_x=True, expand_y=True)],
            [sg.Button("Exit")],
        ]

        desired_size = (1055, 950)
        window = sg.Window(
            "Far Horizons Game Manager",
            layout,
            resizable=True,
            finalize=True,
            size=desired_size,
        )
        clamp_window_to_work_area(window, desired_size)
        return window

    def _log(self, text: str) -> None:
        self.window["-OUTPUT-"].print(text)

    def _load_config(self, update_ui: bool = True) -> None:
        config_value = self.window["-CONFIG-"].get().strip()
        config_path = Path(config_value)
        if not config_path.exists():
            sg.popup_error(f"Config file not found: {config_path}")
            return

        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            sg.popup_error(f"Could not parse config: {exc}")
            return

        games = raw.get("games", [])
        bindir = raw.get("bindir", "")

        if not games:
            sg.popup_error("No games found in config.")
            return

        self.state.config_path = config_path
        self.state.bindir = bindir
        self.state.games = list(games)

        if self.state.selected_game not in self.state.games:
            self.state.selected_game = self.state.games[0]

        self._set_game_from_config(raw)

        if update_ui:
            self._sync_ui_from_state()

        self._log(f"Loaded config: {config_path}")

    def _set_game_from_config(self, raw_cfg: dict) -> None:
        game_name = self.state.selected_game
        if not game_name:
            self.state.game_dir = None
            return

        game_cfg = raw_cfg.get(game_name, {})
        data_dir = game_cfg.get("datadir", "")
        self.state.game_dir = Path(data_dir) if data_dir else None

    def _sync_ui_from_state(self) -> None:
        self.window["-CONFIG-"].update(str(self.state.config_path))
        self.window["-THEME-"].update(value=self.theme_name)
        self.window["-GAME-"].update(values=self.state.games, value=self.state.selected_game)
        self.window["-GAME-DIR-"].update(str(self.state.game_dir or ""))
        self._refresh_files()
        self._refresh_players()
        self._refresh_player_turns()

    def _relaunch_with_theme(self, theme_name: str) -> None:
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--theme",
            theme_name,
            "--config",
            str(self.state.config_path),
        ]
        if self.state.selected_game:
            cmd.extend(["--game", self.state.selected_game])
        subprocess.Popen(cmd, cwd=str(SCRIPT_DIR))

    def _set_preflight_status(self, ok: bool, message: str) -> None:
        color = "lightgreen" if ok else "red"
        self.window["-PREFLIGHT-STATUS-"].update(value=message, text_color=color)

    def _run_preflight_check(self, auto: bool = False) -> None:
        prefix = "[auto-preflight]" if auto else "[preflight]"
        self._log("\n" + "=" * 80)
        self._log(f"{prefix} Checking game management prerequisites")
        self._log("=" * 80)

        failures: list[str] = []

        cfg = self.state.config_path
        if not cfg.exists():
            failures.append(f"Config not found: {cfg}")
        else:
            self._log(f"OK config: {cfg}")

        bindir = Path(self.state.bindir) if self.state.bindir else None
        if not bindir or not bindir.exists():
            failures.append(f"bindir missing or invalid: {self.state.bindir}")
        else:
            self._log(f"OK bindir: {bindir}")

        game_dir = self.state.game_dir
        if not game_dir or not game_dir.exists():
            failures.append(f"game datadir missing or invalid: {self.state.game_dir}")
        else:
            self._log(f"OK datadir: {game_dir}")

        # Probe engine execution early to catch ELF/WSL/.exe issues before a full run.
        if not failures:
            old_cwd = Path.cwd()
            try:
                os.chdir(game_dir)
                out = fhutils.run(self.state.bindir, "TurnNumber")
                probe = out.strip() if out is not None else ""
                self._log(f"OK TurnNumber probe: '{probe}'")
            except SystemExit as exc:
                failures.append(f"TurnNumber probe failed (exit {exc.code}).")
            except Exception as exc:
                failures.append(f"TurnNumber probe failed: {exc}")
            finally:
                os.chdir(old_cwd)

        if failures:
            for fail in failures:
                self._log("FAIL " + fail)
            self._set_preflight_status(False, "Preflight failed. See Output tab for details.")
        else:
            self._set_preflight_status(True, "Preflight passed. Environment is ready.")
            self._log("PASS preflight checks completed successfully")

    def _reload_and_select_game(self, game_name: str) -> None:
        cfg_path = Path(self.window["-CONFIG-"].get().strip())
        if not cfg_path.exists():
            return

        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        self.state.selected_game = game_name
        self._set_game_from_config(raw)
        self.window["-GAME-DIR-"].update(str(self.state.game_dir or ""))
        self._refresh_files()
        self._refresh_players()
        self._refresh_player_turns()
        self._run_preflight_check(auto=True)

    def _validate_context(self) -> bool:
        if not self.state.game_dir or not self.state.game_dir.exists():
            sg.popup_error("Game directory is missing or invalid.")
            return False
        if not self.state.bindir:
            sg.popup_error("bindir is missing in config.")
            return False
        return True

    def _tool_script(self, script_name: str) -> str:
        return str(SCRIPT_DIR / script_name)

    def _run_python_tool(
        self,
        script_name: str,
        extra_args: list[str] | None = None,
        stdin_file: Optional[Path] = None,
    ) -> None:
        if not self._validate_context():
            return

        if extra_args is None:
            extra_args = []

        cmd = [sys.executable, self._tool_script(script_name), "-c", str(self.state.config_path)] + extra_args
        self._run_command(cmd, cwd=self.state.game_dir, stdin_file=stdin_file)

    def _run_command(
        self,
        cmd: list[str],
        cwd: Optional[Path] = None,
        stdin_file: Optional[Path] = None,
    ) -> None:
        self._log("\n" + "=" * 80)
        self._log("Running: " + " ".join(cmd))
        self._log("=" * 80)

        input_data = None
        if stdin_file:
            if not stdin_file.exists():
                sg.popup_error(f"Input file not found: {stdin_file}")
                return
            input_data = stdin_file.read_text(encoding="utf-8", errors="replace")

        try:
            completed = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                input=input_data,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.stdout:
                self._log(completed.stdout)
            if completed.stderr:
                self._log("[stderr]\n" + completed.stderr)
            self._log(f"Exit code: {completed.returncode}")
        except Exception as exc:
            self._log(f"Failed to run command: {exc}")

        self._refresh_files()

    def _run_engine_command(self) -> None:
        if not self._validate_context():
            return
        cmd_name = self.window["-ENGINE-CMD-"].get()
        if not cmd_name:
            return
        self._log("\n" + "=" * 80)
        self._log(f"Running engine command: {cmd_name}")
        self._log("=" * 80)
        old_cwd = Path.cwd()
        try:
            os.chdir(self.state.game_dir)
            output = fhutils.run(self.state.bindir, cmd_name)
            if output:
                self._log(output)
            self._log("Exit code: 0")
        except SystemExit as exc:
            self._log(f"Engine command failed (exit {exc.code}).")
        except Exception as exc:
            self._log(f"Engine command failed: {exc}")
        finally:
            os.chdir(old_cwd)
            self._refresh_files()
            self._refresh_players()
            self._refresh_player_turns()

    def _selected_species_args(self) -> list[str]:
        species = self.window["-SPECIES-"].get().strip()
        if not species:
            return []
        return ["-s", species]

    def _selected_test_args(self) -> list[str]:
        return ["-t"] if self.window["-TEST-MODE-"].get() else []

    def _player_selected_species(self) -> str:
        species = self.window["-PLAYER-SPECIES-"].get().strip()
        return species

    def _player_species_args(self) -> list[str]:
        species = self._player_selected_species()
        if not species:
            return []
        return ["-s", species]

    def _player_test_args(self) -> list[str]:
        return ["-t"] if self.window["-PLAYER-TEST-MODE-"].get() else []

    def _player_orders_status_args(self) -> list[str]:
        args = self._player_test_args() + self._player_species_args()
        if self.window["-PLAYER-EMAIL-ERRORS-"].get():
            args.extend(["-e", "Yes"])
        return args

    def _player_file_candidates(self, species: str) -> tuple[Path, list[Path]]:
        game_dir = self.state.game_dir or Path(".")
        orders = game_dir / f"sp{species}.ord"
        reports = sorted(
            game_dir.glob(f"sp{species}.rpt.t*"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        return orders, reports

    def _turn_history_for_species(self, species: str) -> list[str]:
        if not species or not self.state.game_dir:
            return []

        turns: list[str] = []
        for report in self.state.game_dir.glob(f"sp{species}.rpt.t*"):
            suffix = report.name.split(".rpt.t")[-1].removesuffix(".txt")
            if suffix.isdigit():
                turns.append(suffix)

        turns = sorted(set(turns), key=lambda v: int(v), reverse=True)
        return turns

    def _refresh_player_turns(self) -> None:
        species = self._player_selected_species()
        turns = self._turn_history_for_species(species)
        current_turn = self.window["-PLAYER-TURN-"].get().strip()

        if current_turn and current_turn not in turns:
            turns = [current_turn] + turns

        default_turn = current_turn if current_turn else (turns[0] if turns else "")
        self.window["-PLAYER-TURN-"].update(values=turns, value=default_turn)

    def _set_player_preview(self, text: str) -> None:
        self.window["-PLAYER-PREVIEW-"].update(text)

    def _refresh_players(self) -> None:
        game_dir = self.state.game_dir
        if not game_dir or not game_dir.exists():
            self.window["-PLAYER-LIST-"].update(values=[])
            self._set_player_preview("")
            self.player_rows = []
            return

        fh_names = game_dir / "fh_names"
        if not fh_names.exists():
            self.window["-PLAYER-LIST-"].update(values=[])
            self._set_player_preview("No fh_names file found in game directory.")
            self.player_rows = []
            return

        try:
            lines = [line.strip() for line in fh_names.read_text(encoding="utf-8", errors="replace").splitlines()]
        except OSError as exc:
            self._set_player_preview(f"Could not read fh_names: {exc}")
            return

        self.player_rows = []
        for i in range(0, len(lines), 3):
            chunk = lines[i:i + 3]
            if len(chunk) < 3:
                continue
            sp, name, email = chunk
            self.player_rows.append((sp, name, email))

        self._apply_player_filter()

    def _apply_player_filter(self) -> None:
        query = self.window["-PLAYER-SEARCH-"].get().strip().lower()
        display: list[str] = []
        for sp, name, email in self.player_rows:
            row = f"{sp} | {name} | {email}"
            if not query or query in row.lower():
                display.append(row)

        self.window["-PLAYER-LIST-"].update(values=display)

    def _sync_species_from_player_list(self) -> None:
        selected = self.window["-PLAYER-LIST-"].get()
        if not selected:
            return
        first = selected[0]
        species = first.split("|")[0].strip()
        self.window["-PLAYER-SPECIES-"].update(species)
        self.window["-SPECIES-"].update(species)
        self._refresh_player_turns()

    def _player_preview_orders(self) -> None:
        species = self._player_selected_species()
        if not species:
            sg.popup_error("Set species first in Player Ops tab.")
            return
        orders, _reports = self._player_file_candidates(species)
        self._set_player_preview(file_preview(orders))

    def _player_preview_report(self) -> None:
        species = self._player_selected_species()
        if not species:
            sg.popup_error("Set species first in Player Ops tab.")
            return

        game_dir = self.state.game_dir
        if not game_dir:
            return

        turn = self.window["-PLAYER-TURN-"].get().strip()
        if turn:
            report = game_dir / f"sp{species}.rpt.t{turn}.txt"
            self._set_player_preview(file_preview(report))
            return

        _orders, reports = self._player_file_candidates(species)
        if not reports:
            self._set_player_preview("No report files found for this species.")
            return
        self._set_player_preview(file_preview(reports[0]))

    def _open_player_orders(self) -> None:
        species = self._player_selected_species()
        if not species:
            sg.popup_error("Set species first in Player Ops tab.")
            return
        orders, _reports = self._player_file_candidates(species)
        if not orders.exists():
            sg.popup_error(f"Orders file not found: {orders.name}")
            return
        self._open_path(orders)

    def _open_player_report(self) -> None:
        species = self._player_selected_species()
        if not species:
            sg.popup_error("Set species first in Player Ops tab.")
            return

        game_dir = self.state.game_dir
        if not game_dir:
            return

        turn = self.window["-PLAYER-TURN-"].get().strip()
        if turn:
            report = game_dir / f"sp{species}.rpt.t{turn}.txt"
            if not report.exists():
                sg.popup_error(f"Report file not found: {report.name}")
                return
            self._open_path(report)
            return

        _orders, reports = self._player_file_candidates(species)
        if not reports:
            sg.popup_error("No report files found for this species.")
            return
        self._open_path(reports[0])

    def _launch_order_builder(self, initial_file: Optional[Path] = None) -> None:
        script_path = Path(self._tool_script("order_builder_gui.py"))
        cmd = [sys.executable, str(script_path), "--theme", self.theme_name]

        launch_file = initial_file
        if launch_file is None and self.state.game_dir:
            selected = sg.popup_get_file(
                "Choose a report or orders file",
                initial_folder=str(self.state.game_dir),
                file_types=(("Turn Files", "*.txt;*.ord;*.rpt;*.rpt.t*"), ("All Files", "*.*")),
                no_window=True,
            )
            if selected:
                launch_file = Path(selected)

        if launch_file is not None:
            cmd.append(str(launch_file))

        try:
            subprocess.Popen(cmd, cwd=str(self.state.game_dir) if self.state.game_dir else None)
        except Exception as exc:
            sg.popup_error(f"Could not launch order builder: {exc}")

    def _launch_player_order_builder(self) -> None:
        species = self._player_selected_species()
        if not species:
            sg.popup_error("Set species first in Player Ops tab.")
            return

        game_dir = self.state.game_dir
        if not game_dir:
            sg.popup_error("Game directory is missing or invalid.")
            return

        orders, reports = self._player_file_candidates(species)
        turn = self.window["-PLAYER-TURN-"].get().strip()
        preferred_report = game_dir / f"sp{species}.rpt.t{turn}.txt" if turn else None

        if orders.exists():
            self._launch_order_builder(orders)
            return
        if preferred_report is not None and preferred_report.exists():
            self._launch_order_builder(preferred_report)
            return
        if reports:
            self._launch_order_builder(reports[0])
            return

        sg.popup_error("No orders or report files found for this species.")

    # ------------------------------------------------------------------
    # New Game Wizard
    # ------------------------------------------------------------------

    _PLAYER_COLS = ["Email", "Species", "Home Planet", "Gov Name", "Gov Type", "ML", "GV", "LS", "BI"]
    _TECH_DEFAULTS = {"ML": "1", "GV": "1", "LS": "1", "BI": "1"}

    def _wizard_row_display(self, row: list[str]) -> str:
        return " | ".join(row)

    def _wizard_player_popup(self, title: str = "Add Player", values: list[str] | None = None) -> list[str] | None:
        """Open a popup form to enter/edit one player row.  Returns the 9-field list or None if cancelled."""
        defaults = values if values else ["", "", "", "", "", "1", "1", "1", "1"]
        layout = [
            [sg.Text(col, size=(14, 1)), sg.Input(defaults[i], key=f"-F{i}-", size=(36, 1))]
            for i, col in enumerate(self._PLAYER_COLS)
        ] + [
            [sg.Button("OK"), sg.Button("Cancel")],
        ]
        win = sg.Window(title, layout, modal=True, finalize=True)
        place_window_in_work_area(win)
        result = None
        while True:
            ev, vals = win.read()
            if ev in (sg.WIN_CLOSED, "Cancel"):
                break
            if ev == "OK":
                row = [vals[f"-F{i}-"].strip() for i in range(9)]
                errors = []
                for idx, label in enumerate(["Species", "Home Planet", "Gov Name", "Gov Type"]):
                    v = row[idx + 1]
                    if not v:
                        errors.append(f"{label} cannot be empty.")
                    elif len(v) > 128:
                        errors.append(f"{label} must be ≤ 128 chars (currently {len(v)}).")
                for idx, label in enumerate(["ML", "GV", "LS", "BI"]):
                    v = row[idx + 5]
                    if not v.isdigit():
                        errors.append(f"{label} must be an integer.")
                if errors:
                    sg.popup_error("\n".join(errors), title="Validation Error")
                else:
                    result = row
                    break
        win.close()
        return result

    def _wizard_run_step(self, label: str, cmd: list[str], cwd: Path, log_key: str, win: sg.Window, stdin_text: str | None = None) -> bool:
        """Run one wizard step, stream output to the wizard log.  Returns True on success."""
        win[log_key].print(f"\n{'='*70}")
        win[log_key].print(f"STEP: {label}")
        win[log_key].print(f"CMD:  {' '.join(cmd)}")
        win[log_key].print("=" * 70)
        win.refresh()
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(cwd),
                input=stdin_text,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.stdout:
                win[log_key].print(completed.stdout)
            if completed.stderr:
                win[log_key].print("[stderr]\n" + completed.stderr)
            win[log_key].print(f"Exit code: {completed.returncode}")
            win.refresh()
            if completed.returncode != 0:
                win[log_key].print(f"FAILED at: {label}")
                return False
            return True
        except Exception as exc:
            win[log_key].print(f"ERROR running step '{label}': {exc}")
            win.refresh()
            return False

    def _run_new_game_wizard(self) -> None:
        if not self._validate_context():
            return

        config_path = str(self.state.config_path)
        game_dir = self.state.game_dir
        assert game_dir is not None

        players: list[list[str]] = []

        # ---- Helper to rebuild the player listbox display ----
        def refresh_list(win: sg.Window) -> None:
            win["-WIZ-PLAYERS-"].update(
                values=[self._wizard_row_display(r) for r in players]
            )

        col_header = " | ".join(f"{c:<18}" if i < 5 else f"{c:>3}" for i, c in enumerate(self._PLAYER_COLS))

        layout = [
            [sg.Text("New Game Wizard", font=("Any", 13, "bold"))],
            [sg.HorizontalSeparator()],
            # CSV load/save row
            [
                sg.Text("Signups CSV"),
                sg.Input("", key="-WIZ-CSV-", size=(55, 1)),
                sg.FileBrowse(file_types=(("CSV", "*.csv"),), key="-WIZ-CSV-BROWSE-"),
                sg.Button("Load CSV", key="-WIZ-LOAD-CSV-"),
                sg.Button("Save CSV", key="-WIZ-SAVE-CSV-"),
            ],
            # Column header
            [sg.Text(col_header, font=("Courier", 9), text_color="gray")],
            # Player list
            [sg.Listbox([], key="-WIZ-PLAYERS-", size=(110, 8), font=("Courier", 9), enable_events=True)],
            # Row action buttons
            [
                sg.Button("Add Player", key="-WIZ-ADD-"),
                sg.Button("Edit Selected", key="-WIZ-EDIT-"),
                sg.Button("Remove Selected", key="-WIZ-REMOVE-"),
                sg.Text("", key="-WIZ-PLAYER-COUNT-", size=(20, 1), text_color="blue"),
            ],
            [sg.HorizontalSeparator()],
            # Intro text
            [
                sg.Text("Intro Text"),
                sg.Input(str(game_dir / "intro.txt") if (game_dir / "intro.txt").exists() else "", key="-WIZ-INTRO-", size=(55, 1)),
                sg.FileBrowse(file_types=(("Text", "*.txt;*.md;*.msg"), ("All", "*.*"))),
                sg.Checkbox("Test Mode (no emails sent)", key="-WIZ-TEST-", default=True),
            ],
            [sg.HorizontalSeparator()],
            # Log area
            [sg.Text("Output Log")],
            [sg.Multiline("", key="-WIZ-LOG-", size=(110, 16), autoscroll=True, write_only=True, font=("Courier", 9))],
            [sg.HorizontalSeparator()],
            # Step buttons
            [
                sg.Button("1: Game Setup", key="-WIZ-STEP1-"),
                sg.Button("2: Create Map", key="-WIZ-STEP2-"),
                sg.Button("3: Game Packet", key="-WIZ-STEP3-"),
                sg.Button("4: Inject Intro", key="-WIZ-STEP4-"),
                sg.Button("5: Send Reports", key="-WIZ-STEP5-"),
                sg.Text("  "),
                sg.Button("Run All Steps", key="-WIZ-RUN-ALL-", button_color=("white", "#1a6b2e")),
                sg.Button("Close", key="-WIZ-CLOSE-"),
            ],
        ]

        wizard_size = (920, 720)
        win = sg.Window("New Game Wizard", layout, modal=True, resizable=True, finalize=True, size=wizard_size)
        clamp_window_to_work_area(win, wizard_size)

        def _log(text: str) -> None:
            win["-WIZ-LOG-"].print(text)
            win.refresh()

        def _update_count() -> None:
            win["-WIZ-PLAYER-COUNT-"].update(f"{len(players)} player(s)")

        def _csv_text() -> str:
            import io, csv as csv_mod
            buf = io.StringIO()
            w = csv_mod.writer(buf)
            for r in players:
                w.writerow(r)
            return buf.getvalue()

        def _run_step_game_setup() -> bool:
            if not players:
                _log("ERROR: No players defined. Add players first.")
                return False
            return self._wizard_run_step(
                "Game Setup",
                [sys.executable, self._tool_script("game_setup.py"), "-c", config_path],
                game_dir, "-WIZ-LOG-", win,
                stdin_text=_csv_text(),
            )

        def _run_step_create_map() -> bool:
            return self._wizard_run_step(
                "Create Map",
                [sys.executable, self._tool_script("create_map.py"), "-c", config_path],
                game_dir, "-WIZ-LOG-", win,
            )

        def _run_step_game_packet() -> bool:
            return self._wizard_run_step(
                "Game Packet",
                [sys.executable, self._tool_script("game_packet.py"), "-c", config_path],
                game_dir, "-WIZ-LOG-", win,
            )

        def _run_step_inject_intro() -> bool:
            intro_path_str = win["-WIZ-INTRO-"].get().strip()
            if not intro_path_str:
                _log("ERROR: No intro text file selected.")
                return False
            intro_path = Path(intro_path_str)
            if not intro_path.exists():
                _log(f"ERROR: Intro file not found: {intro_path}")
                return False
            inject_text = intro_path.read_text(encoding="utf-8", errors="replace")
            return self._wizard_run_step(
                "Inject Intro",
                [sys.executable, self._tool_script("turn_inject.py"), "-c", config_path],
                game_dir, "-WIZ-LOG-", win,
                stdin_text=inject_text,
            )

        def _run_step_send_reports() -> bool:
            extra = ["-t"] if win["-WIZ-TEST-"].get() else []
            return self._wizard_run_step(
                "Send Reports",
                [sys.executable, self._tool_script("turn_send.py"), "-c", config_path] + extra,
                game_dir, "-WIZ-LOG-", win,
            )

        while True:
            ev, vals = win.read()

            if ev in (sg.WIN_CLOSED, "-WIZ-CLOSE-"):
                break

            elif ev == "-WIZ-LOAD-CSV-":
                csv_path = vals["-WIZ-CSV-"].strip()
                if not csv_path or not Path(csv_path).exists():
                    sg.popup_error("Select a CSV file first.")
                    continue
                import csv as csv_mod
                loaded = []
                errors = []
                try:
                    with open(csv_path, newline="", encoding="utf-8") as f:
                        for idx, row in enumerate(csv_mod.reader(f), start=1):
                            row = [c.strip() for c in row]
                            if not any(row):
                                continue
                            if len(row) != 9:
                                errors.append(f"Row {idx}: expected 9 fields, got {len(row)}")
                                continue
                            loaded.append(row)
                except Exception as exc:
                    sg.popup_error(f"Could not read CSV: {exc}")
                    continue
                if errors:
                    sg.popup_error("Some rows were skipped:\n" + "\n".join(errors))
                players[:] = loaded
                refresh_list(win)
                _update_count()
                _log(f"Loaded {len(players)} player(s) from {csv_path}")

            elif ev == "-WIZ-SAVE-CSV-":
                csv_path = vals["-WIZ-CSV-"].strip()
                if not csv_path:
                    csv_path = sg.popup_get_file("Save CSV as", save_as=True, file_types=(("CSV", "*.csv"),))
                    if not csv_path:
                        continue
                try:
                    import csv as csv_mod
                    with open(csv_path, "w", newline="", encoding="utf-8") as f:
                        csv_mod.writer(f).writerows(players)
                    _log(f"Saved {len(players)} player(s) to {csv_path}")
                    win["-WIZ-CSV-"].update(csv_path)
                except Exception as exc:
                    sg.popup_error(f"Could not save CSV: {exc}")

            elif ev == "-WIZ-ADD-":
                row = self._wizard_player_popup("Add Player")
                if row:
                    players.append(row)
                    refresh_list(win)
                    _update_count()

            elif ev == "-WIZ-EDIT-":
                selected = win["-WIZ-PLAYERS-"].get_indexes()
                if not selected:
                    sg.popup_error("Select a player row to edit.")
                    continue
                idx = selected[0]
                row = self._wizard_player_popup("Edit Player", values=players[idx])
                if row:
                    players[idx] = row
                    refresh_list(win)

            elif ev == "-WIZ-REMOVE-":
                selected = win["-WIZ-PLAYERS-"].get_indexes()
                if not selected:
                    sg.popup_error("Select a player row to remove.")
                    continue
                idx = selected[0]
                removed = players.pop(idx)
                refresh_list(win)
                _update_count()
                _log(f"Removed player: {removed[1]} ({removed[0]})")

            elif ev == "-WIZ-STEP1-":
                _run_step_game_setup()
                self._refresh_files()
            elif ev == "-WIZ-STEP2-":
                _run_step_create_map()
                self._refresh_files()
            elif ev == "-WIZ-STEP3-":
                _run_step_game_packet()
                self._refresh_files()
            elif ev == "-WIZ-STEP4-":
                _run_step_inject_intro()
                self._refresh_files()
            elif ev == "-WIZ-STEP5-":
                _run_step_send_reports()

            elif ev == "-WIZ-RUN-ALL-":
                _log("\n>>> Starting full new-game setup sequence...\n")
                ok = _run_step_game_setup()
                if ok:
                    ok = _run_step_create_map()
                if ok:
                    ok = _run_step_game_packet()
                if ok:
                    ok = _run_step_inject_intro()
                if ok:
                    _run_step_send_reports()
                _log("\n>>> Wizard sequence complete." if ok else "\n>>> Wizard stopped due to step failure.")
                self._refresh_files()

        win.close()
        self._refresh_files()
        self._refresh_players()
        self._refresh_player_turns()

    def _refresh_files(self) -> None:
        game_dir = self.state.game_dir
        if not game_dir or not game_dir.exists():
            self.window["-FILE-LIST-"].update(values=[])
            self.window["-FILE-PREVIEW-"].update("")
            return

        file_glob = self.window["-FILE-GLOB-"].get().strip() or "*"
        patterns = [part.strip() for part in file_glob.split(",") if part.strip()]
        if not patterns:
            patterns = ["*"]

        files: list[str] = []
        for pattern in patterns:
            for match in glob.glob(str(game_dir / pattern)):
                p = Path(match)
                if p.is_file():
                    files.append(str(p.name))

        files = sorted(set(files), key=lambda v: v.lower())
        self.window["-FILE-LIST-"].update(values=files)

    def _preview_selected_file(self) -> None:
        selected = self.window["-FILE-LIST-"].get()
        if not selected:
            return

        game_dir = self.state.game_dir
        if not game_dir:
            return

        path = game_dir / selected[0]
        self.window["-FILE-PREVIEW-"].update(file_preview(path))

    def _open_selected_file(self) -> None:
        selected = self.window["-FILE-LIST-"].get()
        if not selected or not self.state.game_dir:
            return

        path = self.state.game_dir / selected[0]
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            sg.popup_error(f"Could not open file: {exc}")

    def run(self) -> None:
        while True:
            event, _values = self.window.read()

            if event in (sg.WIN_CLOSED, "Exit"):
                break

            if event == "-LOAD-CONFIG-":
                self._load_config()
                self._run_preflight_check(auto=True)
            elif event == "-APPLY-THEME-":
                selected_theme = self.window["-THEME-"].get()
                if selected_theme in THEME_OPTIONS and selected_theme != self.theme_name:
                    save_theme(selected_theme)
                    self._relaunch_with_theme(selected_theme)
                    break
            elif event == "-GAME-":
                game_name = self.window["-GAME-"].get()
                if game_name:
                    self._reload_and_select_game(game_name)
            elif event == "-RUN-PREFLIGHT-":
                self._run_preflight_check(auto=False)
            elif event == "-OPEN-GAME-DIR-":
                if self.state.game_dir and self.state.game_dir.exists():
                    self._open_path(self.state.game_dir)
            elif event in ("-REFRESH-FILES-", "-FILE-GLOB-"):
                self._refresh_files()
                self._refresh_players()
            elif event == "-FILE-LIST-":
                self._preview_selected_file()
            elif event == "-OPEN-FILE-":
                self._open_selected_file()
            elif event == "-REFRESH-PLAYERS-":
                self._refresh_players()
            elif event == "-PLAYER-SEARCH-":
                self._apply_player_filter()
            elif event == "-PLAYER-LIST-":
                self._sync_species_from_player_list()
            elif event == "-PLAYER-SPECIES-":
                self._refresh_player_turns()
            elif event == "-REFRESH-TURNS-":
                self._refresh_player_turns()

            elif event == "-RUN-NEW-GAME-WIZARD-":
                self._run_new_game_wizard()

            elif event == "-RUN-GAME-SETUP-":
                signups = self.window["-SIGNUPS-"].get().strip()
                if not signups:
                    sg.popup_error("Select a signups CSV file first.")
                else:
                    self._run_python_tool("game_setup.py", stdin_file=Path(signups))

            elif event == "-RUN-CREATE-MAP-":
                self._run_python_tool("create_map.py")
            elif event == "-RUN-GAME-PACKET-":
                self._run_python_tool("game_packet.py")
            elif event == "-RUN-TURN-INJECT-":
                inject_file = self.window["-INJECT-FILE-"].get().strip()
                if not inject_file:
                    sg.popup_error("Select a text file to inject.")
                else:
                    self._run_python_tool("turn_inject.py", stdin_file=Path(inject_file))
            elif event == "-RUN-ORDER-BUILDER-":
                self._launch_order_builder()

            elif event == "-RUN-ORDERS-FETCH-":
                self._run_python_tool("orders_fetch.py")
            elif event == "-RUN-ORDERS-CLEAN-":
                self._run_python_tool("orders_clean.py")
            elif event == "-RUN-ORDERS-STATUS-":
                args = self._selected_test_args() + self._selected_species_args()
                self._run_python_tool("orders_status.py", extra_args=args)
            elif event == "-RUN-TURN-REMINDER-":
                args = self._selected_test_args() + self._selected_species_args()
                self._run_python_tool("turn_reminder.py", extra_args=args)
            elif event == "-RUN-SIGNUPS-VERIFY-":
                self._run_python_tool("signups_verify.py")
            elif event == "-RUN-SIGNUPS-FETCH-":
                self._run_python_tool("signups_fetch.py")

            elif event == "-RUN-TURN-RUN-":
                self._run_python_tool("turn_run.py")
            elif event == "-RUN-TURN-RUN-DISCARD-":
                self._run_python_tool("turn_run.py", extra_args=["--discard"])
            elif event == "-RUN-TURN-CLEAN-":
                self._run_python_tool("turn_clean.py")
            elif event == "-RUN-TURN-CONFIRM-":
                self._run_python_tool("turn_confirm.py")
            elif event == "-RUN-TURN-SAVE-":
                self._run_python_tool("turn_save.py")
            elif event == "-RUN-TURN-SEND-":
                args = self._selected_test_args() + self._selected_species_args()
                self._run_python_tool("turn_send.py", extra_args=args)

            elif event == "-RUN-ENGINE-CMD-":
                self._run_engine_command()

            elif event == "-PLAYER-ORDERS-STATUS-":
                self._run_python_tool("orders_status.py", extra_args=self._player_orders_status_args())
            elif event == "-PLAYER-REMINDER-":
                self._run_python_tool("turn_reminder.py", extra_args=self._player_test_args() + self._player_species_args())
            elif event == "-PLAYER-SEND-REPORT-":
                self._run_python_tool("turn_send.py", extra_args=self._player_test_args() + self._player_species_args())
            elif event == "-PLAYER-PREVIEW-ORDERS-":
                self._player_preview_orders()
            elif event == "-PLAYER-PREVIEW-REPORT-":
                self._player_preview_report()
            elif event == "-PLAYER-OPEN-ORDERS-":
                self._open_player_orders()
            elif event == "-PLAYER-OPEN-REPORT-":
                self._open_player_report()
            elif event == "-PLAYER-ORDER-BUILDER-":
                self._launch_player_order_builder()

        self.window.close()

    def _open_path(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            sg.popup_error(f"Could not open path: {exc}")


def main() -> None:
    theme_name = load_saved_theme()
    config_path: Path | None = None
    selected_game: str | None = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--theme" and i + 1 < len(args):
            if args[i + 1] in THEME_OPTIONS:
                theme_name = args[i + 1]
            i += 2
            continue
        if args[i] == "--config" and i + 1 < len(args):
            config_path = Path(args[i + 1])
            i += 2
            continue
        if args[i] == "--game" and i + 1 < len(args):
            selected_game = args[i + 1]
            i += 2
            continue
        i += 1

    app = FHGameManagerGUI(theme_name=theme_name, config_path=config_path, selected_game=selected_game)
    app.run()


if __name__ == "__main__":
    main()
