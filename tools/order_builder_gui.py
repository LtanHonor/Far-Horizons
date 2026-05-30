#!/usr/bin/env python3
"""Far Horizons order builder GUI.

Load a turn report or existing .ord file, then build an order form by choosing
commands from the rules-defined section lists and appending templated order
lines into the active order text.
"""

from __future__ import annotations

import re
import sys
import json
from pathlib import Path
from typing import NamedTuple

try:
    import FreeSimpleGUI as sg
except ImportError:
    print("FreeSimpleGUI is not installed. Install dependencies with:")
    print("python -m pip install -r pyrequirements.txt")
    raise


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
SCRIPT_DIR = Path(__file__).resolve().parent
GUI_SETTINGS_PATH = SCRIPT_DIR / ".fh_gui_settings.json"


def register_themes() -> None:
    for theme_name, theme_def in THEME_DEFINITIONS.items():
        if hasattr(sg, "theme_add_new"):
            sg.theme_add_new(theme_name, theme_def)
        elif hasattr(sg, "LOOK_AND_FEEL_TABLE"):
            sg.LOOK_AND_FEEL_TABLE[theme_name] = theme_def


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


SECTION_ORDER = [
    "COMBAT",
    "PRE-DEPARTURE",
    "JUMPS",
    "PRODUCTION",
    "POST-ARRIVAL",
    "STRIKES",
]

SECTION_COMMANDS = {
    "COMBAT": ["Attack", "Battle", "Engage", "Haven", "Hide", "Hijack", "Summary", "Target", "Withdraw"],
    "PRE-DEPARTURE": ["Ally", "Base", "Deep", "Destroy", "Disband", "Enemy", "Install", "Land", "Message", "Name", "Neutral", "Orbit", "Repair", "Scan", "Send", "Transfer", "Unload", "Zzz"],
    "JUMPS": ["Jump", "Move", "Pjump", "Visited", "Wormhole"],
    "PRODUCTION": ["Ally", "Ambush", "Build", "Continue", "Develop", "Enemy", "Estimate", "Hide", "Ibuild", "Icontinue", "Intercept", "Neutral", "Production", "Recycle", "Research", "Shipyard", "Upgrade"],
    "POST-ARRIVAL": ["Ally", "Auto", "Deep", "Destroy", "Enemy", "Land", "Message", "Name", "Neutral", "Orbit", "Repair", "Scan", "Send", "Teach", "Telescope", "Terraform", "Transfer", "Zzz"],
    "STRIKES": ["Attack", "Battle", "Engage", "Haven", "Hide", "Hijack", "Summary", "Target", "Withdraw"],
}

SECTION_HINTS = {
    "COMBAT": "Combat commands may only be used in the combat and strike sections.",
    "PRE-DEPARTURE": "These orders execute before jumps.",
    "JUMPS": "Jump and move orders belong only in the jump section.",
    "PRODUCTION": "Build and research orders belong only in production.",
    "POST-ARRIVAL": "These orders execute after jumps and production.",
    "STRIKES": "Strike uses the same command set as combat.",
}

COMMAND_HINTS = {
    "Ally": "Declare a species or contact as allied.",
    "Ambush": "Set an ambush target and committed amount.",
    "Attack": "Attack a chosen target during combat.",
    "Auto": "Let the engine apply automatic post-arrival handling.",
    "Base": "Assign a ship to support a named planet as a base.",
    "Battle": "Set battle handling for a location or battle plan.",
    "Build": "Queue a unit or ship type for production.",
    "Continue": "Continue work already started on a ship or project.",
    "Deep": "Send a ship into deep space status.",
    "Develop": "Spend production to develop a selected item.",
    "Destroy": "Scrap or destroy a specified ship or planet asset.",
    "Disband": "Disband a colony or planetary presence.",
    "Enemy": "Mark a species or contact as hostile.",
    "Engage": "Engage a selected target during combat.",
    "Estimate": "Estimate another species' technology level.",
    "Haven": "Set a haven or fallback location.",
    "Hide": "Attempt to hide a ship or planet asset.",
    "Hijack": "Attempt to hijack a target ship.",
    "Ibuild": "Queue immediate build work in production.",
    "Icontinue": "Continue immediate build work already underway.",
    "Install": "Install a quantity of an item on a planet.",
    "Intercept": "Assign a ship to intercept a target.",
    "Jump": "Jump a ship to a chosen set of coordinates.",
    "Land": "Land a ship on a named planet.",
    "Message": "Send freeform text to another empire.",
    "Move": "Move a ship to another location without a jump order.",
    "Name": "Rename a ship, planet, or other named object.",
    "Neutral": "Mark a species or contact as neutral.",
    "Orbit": "Put a ship into orbit around a planet.",
    "Pjump": "Perform a probability jump to a location.",
    "Production": "Open or repeat a planet production block.",
    "Recycle": "Recycle units, items, or ships for recovery.",
    "Repair": "Allocate work to repair a ship.",
    "Research": "Spend production on a specific tech field.",
    "Scan": "Scan a ship or location for information.",
    "Send": "Send items or a message package to a recipient.",
    "Shipyard": "Increase or assign shipyard capacity.",
    "Summary": "Request the combat summary output.",
    "Target": "Set targeting priority or a preferred unit.",
    "Teach": "Teach a technology to another species.",
    "Telescope": "Observe a distant location with telescope orders.",
    "Terraform": "Terraform a planet using available effort.",
    "Transfer": "Transfer a quantity of an item between sources.",
    "Unload": "Unload cargo from a ship.",
    "Upgrade": "Upgrade a ship or base with a selected item.",
    "Visited": "Mark a ship or location as visited.",
    "Withdraw": "Withdraw a target from combat engagement.",
    "Wormhole": "Send a ship through a wormhole destination.",
    "Zzz": "No action for this slot or section.",
}

ITEM_CHOICES = [
    "RM", "PD", "SU", "DR", "CU", "IU", "AU", "FS", "JP", "FM", "FJ", "GT", "FD", "TP", "GW",
    "SG1", "SG2", "SG3", "SG4", "SG5", "SG6", "SG7", "SG8", "SG9",
    "GU1", "GU2", "GU3", "GU4", "GU5", "GU6", "GU7", "GU8", "GU9",
]
TECH_CHOICES = ["Mining", "Manufacturing", "Military", "Gravitics", "Life Support", "Biology", "MI", "MA", "ML", "GV", "LS", "BI"]

ITEM_HINTS = {
    "RM": "Raw materials",
    "PD": "Planetary defense unit",
    "SU": "Supply unit",
    "DR": "Damage repair unit",
    "CU": "Colonist unit",
    "IU": "Industrial unit",
    "AU": "Agricultural unit",
    "FS": "Factory ship component",
    "JP": "Jump portal component",
    "FM": "Fuel module",
    "FJ": "Jump fuel",
    "GT": "Gun turret",
    "FD": "Field distortion unit",
    "TP": "Transport pod",
    "GW": "Gravitic wave unit",
    "SG1": "Starbase gun level 1",
    "SG2": "Starbase gun level 2",
    "SG3": "Starbase gun level 3",
    "SG4": "Starbase gun level 4",
    "SG5": "Starbase gun level 5",
    "SG6": "Starbase gun level 6",
    "SG7": "Starbase gun level 7",
    "SG8": "Starbase gun level 8",
    "SG9": "Starbase gun level 9",
    "GU1": "Ground unit level 1",
    "GU2": "Ground unit level 2",
    "GU3": "Ground unit level 3",
    "GU4": "Ground unit level 4",
    "GU5": "Ground unit level 5",
    "GU6": "Ground unit level 6",
    "GU7": "Ground unit level 7",
    "GU8": "Ground unit level 8",
    "GU9": "Ground unit level 9",
}

SHIP_HINT_SUFFIX = " [loaded ship]"

SPACESHIP_CLASSES = [
    ("PB", 2, "Picketboat", 10000),
    ("CT", 4, "Corvette", 20000),
    ("ES", 10, "Escort", 50000),
    ("FF", 20, "Frigate", 100000),
    ("DD", 30, "Destroyer", 150000),
    ("CL", 40, "Light Cruiser", 200000),
    ("CS", 50, "Strike Cruiser", 250000),
    ("CA", 60, "Heavy Cruiser", 300000),
    ("CC", 70, "Command Cruiser", 350000),
    ("BC", 80, "Battlecruiser", 400000),
    ("BS", 90, "Battleship", 450000),
    ("DN", 100, "Dreadnought", 500000),
    ("SD", 110, "Super Dreadnought", 550000),
    ("BM", 120, "Battlemoon", 600000),
    ("BW", 130, "Battleworld", 650000),
    ("BR", 140, "Battlestar", 700000),
]


class TurnContext(NamedTuple):
    species_name: str
    planets: list[str]
    ships: list[str]
    locations: list[str]
    manufacturing_tech: int | None
    source_text: str
    order_text: str
    file_path: str


class ParamSpec(NamedTuple):
    key: str
    label: str
    kind: str


MAX_PARAM_ROWS = 5

COMMAND_SCHEMAS: dict[str, list[ParamSpec]] = {
    "Ally": [ParamSpec("contact", "Species / Contact", "text")],
    "Ambush": [ParamSpec("target", "Ship / Planet", "combo-any"), ParamSpec("amount", "Amount", "text")],
    "Attack": [ParamSpec("target", "Target", "combo-any")],
    "Auto": [],
    "Base": [ParamSpec("ship", "Ship", "ship"), ParamSpec("planet", "Planet", "planet")],
    "Battle": [ParamSpec("target", "Location / Plan", "location")],
    "Build": [ParamSpec("item", "Item / Ship", "combo-build-item"), ParamSpec("ship_name", "Ship Name", "text"), ParamSpec("amount", "Spend", "text")],
    "Continue": [ParamSpec("ship", "Ship", "ship"), ParamSpec("amount", "Spend", "text")],
    "Deep": [ParamSpec("ship", "Ship", "ship")],
    "Develop": [ParamSpec("item", "Item", "combo-item"), ParamSpec("amount", "Amount", "text")],
    "Destroy": [ParamSpec("target", "Ship / Planet", "combo-any")],
    "Disband": [ParamSpec("planet", "Planet", "planet")],
    "Enemy": [ParamSpec("contact", "Species / Contact", "text")],
    "Engage": [ParamSpec("target", "Target", "combo-any")],
    "Estimate": [ParamSpec("contact", "Species", "text"), ParamSpec("tech", "Tech", "tech")],
    "Haven": [ParamSpec("location", "Location", "location")],
    "Hide": [ParamSpec("target", "Ship / Planet", "combo-any")],
    "Hijack": [ParamSpec("target", "Target Ship", "ship")],
    "Ibuild": [ParamSpec("item", "Item / Ship", "combo-build-item"), ParamSpec("ship_name", "Ship Name", "text"), ParamSpec("amount", "Spend", "text")],
    "Icontinue": [ParamSpec("ship", "Ship", "ship"), ParamSpec("amount", "Spend", "text")],
    "Install": [ParamSpec("amount", "Amount", "text"), ParamSpec("item", "Item", "combo-item"), ParamSpec("planet", "Planet", "planet")],
    "Intercept": [ParamSpec("ship", "Ship", "ship"), ParamSpec("target", "Target", "combo-any")],
    "Jump": [ParamSpec("ship", "Ship", "ship"), ParamSpec("location", "Location", "location")],
    "Land": [ParamSpec("ship", "Ship", "ship"), ParamSpec("planet", "Planet", "planet")],
    "Message": [ParamSpec("recipient", "Recipient", "text"), ParamSpec("message", "Message Text", "long-text")],
    "Move": [ParamSpec("ship", "Ship", "ship"), ParamSpec("location", "Location", "location")],
    "Name": [ParamSpec("target", "Current Name", "combo-any"), ParamSpec("new_name", "New Name", "text")],
    "Neutral": [ParamSpec("contact", "Species / Contact", "text")],
    "Orbit": [ParamSpec("ship", "Ship", "ship"), ParamSpec("planet", "Planet", "planet")],
    "Pjump": [ParamSpec("ship", "Ship", "ship"), ParamSpec("location", "Location", "location")],
    "Production": [ParamSpec("planet", "Planet", "planet")],
    "Recycle": [ParamSpec("item", "Item / Ship", "combo-item"), ParamSpec("amount", "Amount", "text")],
    "Repair": [ParamSpec("ship", "Ship", "ship"), ParamSpec("amount", "Amount", "text")],
    "Research": [ParamSpec("tech", "Tech", "tech"), ParamSpec("amount", "Amount", "text")],
    "Scan": [ParamSpec("target", "Ship / Location", "combo-any")],
    "Send": [ParamSpec("recipient", "Recipient", "text"), ParamSpec("item", "Item", "combo-item"), ParamSpec("amount", "Amount", "text")],
    "Shipyard": [ParamSpec("amount", "Amount", "text")],
    "Summary": [],
    "Target": [ParamSpec("target", "Priority / Unit", "text")],
    "Teach": [ParamSpec("recipient", "Species", "text"), ParamSpec("tech", "Tech", "tech"), ParamSpec("limit", "Limit", "text")],
    "Telescope": [ParamSpec("location", "Location", "location")],
    "Terraform": [ParamSpec("planet", "Planet", "planet"), ParamSpec("amount", "Amount", "text")],
    "Transfer": [ParamSpec("amount", "Amount", "text"), ParamSpec("item", "Item", "combo-item"), ParamSpec("source", "Source", "combo-any"), ParamSpec("destination", "Destination", "combo-any")],
    "Unload": [ParamSpec("ship", "Ship", "ship"), ParamSpec("amount", "Amount", "text"), ParamSpec("item", "Item", "combo-item")],
    "Upgrade": [ParamSpec("target", "Ship / Base", "combo-any"), ParamSpec("item", "Item", "combo-item"), ParamSpec("amount", "Amount", "text")],
    "Visited": [ParamSpec("target", "Ship / Location", "combo-any")],
    "Withdraw": [ParamSpec("target", "Ship / Target", "combo-any")],
    "Wormhole": [ParamSpec("ship", "Ship", "ship"), ParamSpec("location", "Location", "location")],
    "Zzz": [],
}


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def unique_preserve(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        clean_item = item.strip()
        if not clean_item or clean_item in seen:
            continue
        seen.add(clean_item)
        result.append(clean_item)
    return result


def command_option_label(command: str) -> str:
    hint = COMMAND_HINTS.get(command, "")
    return f"{command} - {hint}" if hint else command


def parse_command_option(value: str) -> str:
    if not value:
        return ""
    return value.split(" - ", 1)[0].strip()


def item_option_label(item: str) -> str:
    hint = ITEM_HINTS.get(item, "")
    return f"{item} - {hint}" if hint else item


def parse_item_option(value: str) -> str:
    if not value:
        return ""
    return value.split(" - ", 1)[0].strip()


def ship_option_label(ship: str) -> str:
    return f"{ship}{SHIP_HINT_SUFFIX}" if ship else ship


def parse_ship_option(value: str) -> str:
    if value.endswith(SHIP_HINT_SUFFIX):
        return value[: -len(SHIP_HINT_SUFFIX)].strip()
    return value.strip()


def ship_class_option_label(abbr: str, min_ma: int, class_name: str, tonnage: int) -> str:
    return f"{abbr} - {class_name} ({tonnage:,} tons, min MA {min_ma})"


def sublight_ship_class_option_label(abbr: str, min_ma: int, class_name: str, tonnage: int) -> str:
    return f"{abbr}S - Sub-light {class_name} ({tonnage:,} tons, min MA {min_ma})"


def transport_option_label(size: int, sublight: bool = False) -> str:
    identifier = f"TR{size}{'S' if sublight else ''}"
    tonnage = size * 10000
    capacity = (10 + size // 2) * size
    min_ma = size * 2
    cost = size * (75 if sublight else 100)
    drive = "sub-light" if sublight else "FTL"
    return f"{identifier} - Transport ({tonnage:,} tons, cap {capacity}, {drive} cost {cost}, min MA {min_ma})"


def starbase_option_label() -> str:
    return "BAS - Starbase (size set by spend amount; spend required)"


def is_warship_class_identifier(value: str) -> bool:
    return any(abbr == value or f"{abbr}S" == value for abbr, _min_ma, _class_name, _tonnage in SPACESHIP_CLASSES)


def is_transport_identifier(value: str) -> bool:
    return re.fullmatch(r"TR\d+S?", value) is not None


def is_named_build_identifier(value: str) -> bool:
    return value == "BAS" or is_warship_class_identifier(value) or is_transport_identifier(value)


def transport_size_limit(current_ma: int | None) -> int:
    if current_ma is None:
        return 20
    return max(1, current_ma // 2)


def extract_manufacturing_tech(text: str) -> int | None:
    match = re.search(r"^\s*Manufacturing\s*=\s*(\d+)\s*$", text, flags=re.MULTILINE)
    if match:
        return int(match.group(1))
    fallback = re.search(r"\(MA\s*=\s*(\d+)\)", text)
    if fallback:
        return int(fallback.group(1))
    return None


def extract_species_name(text: str) -> str:
    match = re.search(r"^Species name:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_planets(text: str) -> list[str]:
    planets = []
    planets.extend(re.findall(r"^HOME PLANET:\s+PL\s+(.+)$", text, flags=re.MULTILINE))
    planets.extend(re.findall(r"^\s*PRODUCTION\s+PL\s+(.+)$", text, flags=re.MULTILINE))
    planets.extend(re.findall(r"^Ships at PL\s+(.+):$", text, flags=re.MULTILINE))
    return unique_preserve(planets)


def extract_ships(text: str) -> list[str]:
    ships = re.findall(r"^\s{2,}(.+?)\s+\([A-Z0-9,]+\)\s+\d+", text, flags=re.MULTILINE)
    ships.extend(re.findall(r"^\s*(?:Jump|Move|Pjump|Wormhole|Orbit|Land|Scan|Continue|Unload|Repair)\t([^,\n]+)", text, flags=re.MULTILINE))
    return unique_preserve(ships)


def extract_locations(text: str) -> list[str]:
    locations = []
    for x, y, z in re.findall(r"Coordinates:\s*x\s*=\s*(\d+)\s*y\s*=\s*(\d+)\s*z\s*=\s*(\d+)", text, flags=re.MULTILINE):
        locations.append(f"{x} {y} {z}")
    for x, y, z, pn in re.findall(r"Coordinates:\s*x\s*=\s*(\d+),\s*y\s*=\s*(\d+),\s*z\s*=\s*(\d+),\s*planet number\s*(\d+)", text, flags=re.MULTILINE):
        locations.append(f"{x} {y} {z} #{pn}")
        locations.append(f"{x} {y} {z}")
    for coords in re.findall(r"^\s*(?:Jump|Move|Pjump|Wormhole)\t[^,\n]+,\s*(\d+\s+\d+\s+\d+)", text, flags=re.MULTILINE):
        locations.append(coords)
    return unique_preserve(locations)


def default_order_text(planets: list[str]) -> str:
    lines = []
    for section in SECTION_ORDER:
        lines.append(f"START {section}")
        if section == "PRODUCTION" and planets:
            lines.append("")
            for planet in planets:
                lines.append(f"    PRODUCTION PL {planet}")
                lines.append(f"    ; Enter production orders here for {planet}.")
                lines.append("")
        else:
            lines.append(f"; {section.title()} orders belong here.")
            lines.append("")
        lines.append("END")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def extract_order_text(text: str, planets: list[str]) -> str:
    start_markers = [f"START {section}" for section in SECTION_ORDER]
    first_positions = [text.find(marker) for marker in start_markers if text.find(marker) != -1]
    if first_positions:
        start = min(first_positions)
        return text[start:].strip() + "\n"
    return default_order_text(planets)


def load_turn_context(path: Path) -> TurnContext:
    text = normalize_text(path.read_text(encoding="utf-8", errors="replace"))
    planets = extract_planets(text)
    return TurnContext(
        species_name=extract_species_name(text),
        planets=planets,
        ships=extract_ships(text),
        locations=extract_locations(text),
        manufacturing_tech=extract_manufacturing_tech(text),
        source_text=text,
        order_text=extract_order_text(text, planets),
        file_path=str(path),
    )


def choice_values(kind: str, context: TurnContext | None) -> list[str]:
    if kind == "planet":
        return context.planets if context else []
    if kind == "ship":
        return [ship_option_label(ship) for ship in context.ships] if context else []
    if kind == "location":
        return context.locations if context else []
    if kind == "combo-item":
        return [item_option_label(item) for item in ITEM_CHOICES]
    if kind == "combo-build-item":
        values = [item_option_label(item) for item in ITEM_CHOICES]
        current_ma = context.manufacturing_tech if context else None
        for abbr, min_ma, class_name, tonnage in SPACESHIP_CLASSES:
            if current_ma is None or current_ma >= min_ma:
                values.append(ship_class_option_label(abbr, min_ma, class_name, tonnage))
                values.append(sublight_ship_class_option_label(abbr, min_ma, class_name, tonnage))
        for size in range(1, transport_size_limit(current_ma) + 1):
            min_ma = size * 2
            if current_ma is None or current_ma >= min_ma:
                values.append(transport_option_label(size))
                values.append(transport_option_label(size, sublight=True))
        if current_ma is None or current_ma >= 2:
            values.append(starbase_option_label())
        return unique_preserve(values)
    if kind == "tech":
        return TECH_CHOICES
    if kind == "combo-any":
        values: list[str] = []
        if context:
            values.extend(context.ships)
            values.extend(context.planets)
            values.extend(context.locations)
        values.extend(ITEM_CHOICES)
        return unique_preserve(values)
    return []


def build_simple_line(command: str, args: list[str]) -> str:
    args = [arg.strip() for arg in args if arg.strip()]
    if not args:
        return command
    return f"{command}\t" + ", ".join(args)


def build_named_ship_line(command: str, ship: str, spend: str) -> str:
    named_ship = ship.strip() or "[ship]"
    spend_value = spend.strip()
    if spend_value:
        return f"{command}\t{named_ship}, {spend_value}"
    return f"{command}\t{named_ship}"


def build_order_line(command: str, values: dict[str, str]) -> str:
    if command in {"Auto", "Summary", "Zzz"}:
        return command
    if command == "Production":
        return f"PRODUCTION PL {values.get('planet') or '[planet]'}"
    if command in {"Jump", "Move", "Pjump", "Wormhole"}:
        return f"{command}\t{values.get('ship') or '[ship]'}, {values.get('location') or '[x y z]'}"
    if command in {"Orbit", "Land"}:
        return f"{command}\t{values.get('ship') or '[ship]'}, PL {values.get('planet') or '[planet]'}"
    if command == "Install":
        return f"Install\t{values.get('amount') or '[amount]'} {values.get('item') or '[item]'} PL {values.get('planet') or '[planet]'}"
    if command == "Terraform":
        return f"Terraform\tPL {values.get('planet') or '[planet]'}, {values.get('amount') or '[amount]'}"
    if command == "Research":
        return f"Research\t{values.get('tech') or '[tech]'}, {values.get('amount') or '[amount]'}"
    if command == "Teach":
        return f"Teach\t{values.get('recipient') or '[species]'}, {values.get('tech') or '[tech]'}, {values.get('limit') or '[limit]'}"
    if command == "Transfer":
        return f"Transfer\t{values.get('amount') or '[amount]'} {values.get('item') or '[item]'}, {values.get('source') or '[source]'}, {values.get('destination') or '[destination]'}"
    if command == "Message":
        return f"Message\t{values.get('recipient') or '[recipient]'}, {values.get('message') or '[text]'}"
    if command == "Name":
        return f"Name\t{values.get('target') or '[current]'}, {values.get('new_name') or '[new name]'}"
    if command == "Send":
        return f"Send\t{values.get('recipient') or '[recipient]'}, {values.get('item') or '[item]'}, {values.get('amount') or '[amount]'}"
    if command in {"Build", "Ibuild"}:
        build_target = values.get("item") or "[item or ship]"
        if is_named_build_identifier(build_target):
            ship_name = values.get("ship_name") or "[ship name]"
            spend = values.get("amount", "").strip()
            if build_target == "BAS" and not spend:
                spend = "[amount]"
            if spend:
                return f"{command}\t{build_target} {ship_name}, {spend}"
            return f"{command}\t{build_target} {ship_name}"
        return build_simple_line(command, [build_target])
    if command in {"Continue", "Icontinue"}:
        return build_named_ship_line(command, values.get("ship", ""), values.get("amount", ""))
    if command == "Shipyard":
        return build_simple_line(command, [values.get("amount") or "[amount]"])
    schema = COMMAND_SCHEMAS.get(command, [])
    ordered = [values.get(spec.key, "") for spec in schema if values.get(spec.key, "")]
    return build_simple_line(command, ordered)


def append_to_section(order_text: str, section: str, new_line: str) -> str:
    lines = order_text.splitlines()
    start_idx = None
    end_idx = None
    for index, line in enumerate(lines):
        if line.strip() == f"START {section}":
            start_idx = index
            continue
        if start_idx is not None and line.strip() == "END":
            end_idx = index
            break

    if start_idx is None or end_idx is None:
        if not order_text.endswith("\n"):
            order_text += "\n"
        order_text += f"START {section}\nEND\n"
        return append_to_section(order_text, section, new_line)

    insert_line = f"    {new_line}" if not new_line.startswith("    ") else new_line
    lines.insert(end_idx, insert_line)
    return "\n".join(lines).rstrip() + "\n"


def update_command_values(window: sg.Window, section: str) -> None:
    commands = SECTION_COMMANDS.get(section, [])
    option_labels = [command_option_label(command) for command in commands]
    default_command = option_labels[0] if option_labels else ""
    window["-COMMAND-"].update(values=option_labels, value=default_command)
    window["-SECTION-HINT-"].update(SECTION_HINTS.get(section, ""))
    selected_command = parse_command_option(default_command)
    window["-COMMAND-HINT-"].update(COMMAND_HINTS.get(selected_command, ""))


def field_value(window: sg.Window, row: int) -> str:
    combo_value = window[f"-P{row}-COMBO-"].get()
    input_value = window[f"-P{row}-INPUT-"].get()
    return (combo_value or input_value or "").strip()


def normalized_field_value(kind: str, value: str) -> str:
    if kind == "ship":
        return parse_ship_option(value)
    if kind in {"combo-item", "combo-build-item"}:
        return parse_item_option(value)
    return value


def current_command_values(window: sg.Window, command: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for row, spec in enumerate(COMMAND_SCHEMAS.get(command, [])):
        values[spec.key] = normalized_field_value(spec.kind, field_value(window, row))
    return values


def update_command_form(window: sg.Window, context: TurnContext | None, command: str) -> None:
    command = parse_command_option(command)
    schema = COMMAND_SCHEMAS.get(command, [])
    for row in range(MAX_PARAM_ROWS):
        label_key = f"-P{row}-LABEL-"
        combo_key = f"-P{row}-COMBO-"
        input_key = f"-P{row}-INPUT-"
        if row >= len(schema):
            window[label_key].update(value="", visible=False)
            window[combo_key].update(value="", values=[], visible=False)
            window[input_key].update(value="", visible=False)
            continue
        spec = schema[row]
        window[label_key].update(value=spec.label, visible=True)
        choices = choice_values(spec.kind, context)
        use_combo = spec.kind in {"planet", "ship", "location", "combo-item", "combo-build-item", "tech", "combo-any"}
        if use_combo:
            window[combo_key].update(values=choices, value=choices[0] if choices else "", visible=True)
            window[input_key].update(value="", visible=False)
        else:
            window[combo_key].update(values=[], value="", visible=False)
            window[input_key].update(value="", visible=True)


def refresh_preview(window: sg.Window) -> None:
    section = window["-SECTION-"].get()
    command = parse_command_option(window["-COMMAND-"].get())
    if not section or not command:
        window["-PREVIEW-"].update("")
        window["-COMMAND-HINT-"].update("")
        return
    window["-COMMAND-HINT-"].update(COMMAND_HINTS.get(command, ""))
    window["-PREVIEW-"].update(build_order_line(command, current_command_values(window, command)))


def build_layout(theme_name: str) -> list[list[sg.Element]]:
    sg.theme(theme_name)
    param_rows = []
    for row in range(MAX_PARAM_ROWS):
        param_rows.append([
            sg.Text("", key=f"-P{row}-LABEL-", size=(14, 1), visible=False),
            sg.Combo([], key=f"-P{row}-COMBO-", size=(50, 1), readonly=False, enable_events=True, visible=False),
            sg.Input("", key=f"-P{row}-INPUT-", size=(50, 1), enable_events=True, visible=False),
        ])
    return [
        [
            sg.Text("Theme"),
            sg.Combo(THEME_OPTIONS, default_value=theme_name, key="-THEME-", readonly=True, size=(22, 1)),
            sg.Button("Apply Theme", key="-APPLY-THEME-"),
        ],
        [
            sg.Text("Turn File"),
            sg.Input(key="-FILE-", size=(70, 1)),
            sg.FileBrowse(file_types=(("Turn Files", "*.txt;*.ord;*.rpt;*.rpt.t*"), ("All Files", "*.*"))),
            sg.Button("Load", key="-LOAD-"),
            sg.Button("Save Orders As", key="-SAVE-"),
        ],
        [
            sg.Text("Species", size=(8, 1)),
            sg.Text("", key="-SPECIES-", size=(28, 1)),
            sg.Text("Planets"),
            sg.Text("", key="-PLANET-SUMMARY-", size=(58, 1)),
        ],
        [
            sg.Frame(
                "Command Builder",
                [
                    [
                        sg.Text("Section"),
                        sg.Combo(SECTION_ORDER, default_value=SECTION_ORDER[0], key="-SECTION-", readonly=True, enable_events=True, size=(18, 1)),
                        sg.Text("Command"),
                        sg.Combo([], key="-COMMAND-", readonly=True, enable_events=True, size=(52, 1)),
                    ],
                    [sg.Text("", key="-SECTION-HINT-", size=(84, 2))],
                    [sg.Text("", key="-COMMAND-HINT-", size=(84, 2))],
                    *param_rows,
                    [
                        sg.Text("Preview", size=(14, 1)),
                        sg.Input("", key="-PREVIEW-", size=(68, 1), readonly=True),
                        sg.Button("Append", key="-APPEND-"),
                    ],
                ],
                expand_x=True,
            )
        ],
        [
            sg.Frame(
                "Loaded Turn File",
                [[sg.Multiline("", key="-SOURCE-", size=(72, 28), disabled=True, expand_x=True, expand_y=True)]],
                expand_x=True,
                expand_y=True,
            ),
            sg.Frame(
                "Order Form",
                [[sg.Multiline("", key="-ORDER-", size=(72, 28), expand_x=True, expand_y=True)]],
                expand_x=True,
                expand_y=True,
            ),
        ],
        [sg.StatusBar("Load a turn report or .ord file to begin.", key="-STATUS-", expand_x=True)],
    ]


def load_context_into_window(window: sg.Window, context: TurnContext) -> None:
    window["-SOURCE-"].update(context.source_text)
    window["-ORDER-"].update(context.order_text)
    window["-SPECIES-"].update(context.species_name or "Unknown")
    window["-PLANET-SUMMARY-"].update(", ".join(context.planets) if context.planets else "No planets parsed")


def prompt_save_path(context: TurnContext | None) -> str:
    default_name = "orders.ord"
    if context is not None:
        default_name = Path(context.file_path).with_suffix(".ord").name
    return sg.popup_get_file(
        "Save order form",
        save_as=True,
        default_extension=".ord",
        default_path=default_name,
        file_types=(("Orders", "*.ord"), ("Text", "*.txt")),
        no_window=True,
    ) or ""


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    register_themes()
    theme_name = load_saved_theme()
    initial_file_arg = ""
    i = 0
    while i < len(argv):
        if argv[i] == "--theme" and i + 1 < len(argv):
            candidate = argv[i + 1]
            if candidate in THEME_OPTIONS:
                theme_name = candidate
            i += 2
            continue
        if not initial_file_arg:
            initial_file_arg = argv[i]
        i += 1

    window = sg.Window("Far Horizons Order Builder", build_layout(theme_name), resizable=True, finalize=True)
    context: TurnContext | None = None
    update_command_values(window, SECTION_ORDER[0])
    update_command_form(window, None, window["-COMMAND-"].get())
    refresh_preview(window)

    if initial_file_arg:
        initial_path = Path(initial_file_arg)
        if initial_path.exists():
            context = load_turn_context(initial_path)
            load_context_into_window(window, context)
            window["-FILE-"].update(str(initial_path))
            update_command_form(window, context, window["-COMMAND-"].get())
            refresh_preview(window)
            window["-STATUS-"].update(f"Loaded {initial_path.name}")

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            break

        if event == "-APPLY-THEME-":
            selected_theme = values.get("-THEME-", "")
            if selected_theme not in THEME_OPTIONS or selected_theme == theme_name:
                continue
            save_theme(selected_theme)
            current_file = window["-FILE-"].get().strip()
            current_order = window["-ORDER-"].get()
            current_section = window["-SECTION-"].get()
            current_command = window["-COMMAND-"].get()
            theme_name = selected_theme
            window.close()
            window = sg.Window("Far Horizons Order Builder", build_layout(theme_name), resizable=True, finalize=True)
            update_command_values(window, SECTION_ORDER[0])
            if context is not None:
                load_context_into_window(window, context)
            if current_file:
                window["-FILE-"].update(current_file)
            if current_section in SECTION_ORDER:
                window["-SECTION-"].update(current_section)
                update_command_values(window, current_section)
            if current_command:
                window["-COMMAND-"].update(value=current_command)
            update_command_form(window, context, window["-COMMAND-"].get())
            if current_order:
                window["-ORDER-"].update(current_order)
            refresh_preview(window)
            window["-STATUS-"].update(f"Theme set to {theme_name}.")
            continue

        if event == "-LOAD-":
            file_value = values["-FILE-"]
            if not file_value:
                window["-STATUS-"].update("Choose a turn/report/order file first.")
                continue
            path = Path(file_value)
            if not path.exists():
                window["-STATUS-"].update(f"File not found: {path}")
                continue
            try:
                context = load_turn_context(path)
            except OSError as exc:
                window["-STATUS-"].update(f"Could not load file: {exc}")
                continue
            load_context_into_window(window, context)
            update_command_form(window, context, values["-COMMAND-"])
            refresh_preview(window)
            window["-STATUS-"].update(f"Loaded {path.name}")
            continue

        if event == "-SAVE-":
            order_text = values["-ORDER-"]
            if not order_text.strip():
                window["-STATUS-"].update("There are no orders to save.")
                continue
            save_path = prompt_save_path(context)
            if not save_path:
                continue
            try:
                Path(save_path).write_text(normalize_text(order_text), encoding="utf-8")
            except OSError as exc:
                window["-STATUS-"].update(f"Could not save orders: {exc}")
                continue
            window["-STATUS-"].update(f"Saved order form to {save_path}")
            continue

        if event == "-SECTION-":
            update_command_values(window, values["-SECTION-"])
            update_command_form(window, context, window["-COMMAND-"].get())
            refresh_preview(window)
            continue

        if event == "-COMMAND-":
            update_command_form(window, context, values["-COMMAND-"])
            refresh_preview(window)
            continue

        if event.startswith("-P"):
            refresh_preview(window)
            continue

        if event == "-APPEND-":
            section = values["-SECTION-"]
            command = parse_command_option(values["-COMMAND-"])
            if not section or not command:
                window["-STATUS-"].update("Choose a section and command first.")
                continue
            new_line = build_order_line(command, current_command_values(window, command))
            updated = append_to_section(values["-ORDER-"], section, new_line)
            window["-ORDER-"].update(updated)
            window["-STATUS-"].update(f"Appended '{command}' to {section}.")
            continue

    window.close()


if __name__ == "__main__":
    main()
