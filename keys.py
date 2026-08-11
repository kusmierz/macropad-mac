#!/usr/bin/env python3
"""
Key map for macOS — virtual key codes, names, and display labels.

One source of truth: available keys, their names, how they appear to users, and
how an actual key press is translated into a binding.
"""

# ── name -> virtual key code ────────────────────────────────────────────
LETTERS = {c: k for c, k in zip(
    "abcdefghijklmnopqrstuvwxyz",
    (0, 11, 8, 2, 14, 3, 5, 4, 34, 38, 40, 37, 46, 45, 31, 35, 12, 15,
     1, 17, 32, 9, 13, 7, 16, 6))}

DIGITS = {str(d): k for d, k in zip(
    range(10), (29, 18, 19, 20, 21, 23, 22, 26, 28, 25))}

FKEYS = {**{f"f{i}": k for i, k in zip(range(1, 13),
             (122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111))},
         **{f"f{i}": k for i, k in zip(range(13, 21),
             (105, 107, 113, 106, 64, 79, 80, 90))}}

PUNCT = {
    "minus": 27, "equal": 24, "grave": 50, "lbracket": 33, "rbracket": 30,
    "semicolon": 41, "quote": 39, "comma": 43, "dot": 47, "slash": 44,
    "backslash": 42,
}

CONTROL = {
    "enter": 36, "tab": 48, "space": 49, "backspace": 51, "esc": 53,
    "delete": 117, "help": 114,
}

NAV = {
    "left": 123, "right": 124, "down": 125, "up": 126,
    "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
}

KEYPAD = {
    "num0": 82, "num1": 83, "num2": 84, "num3": 85, "num4": 86, "num5": 87,
    "num6": 88, "num7": 89, "num8": 91, "num9": 92,
    "numdot": 65, "numplus": 69, "numminus": 78, "nummultiply": 67,
    "numdivide": 75, "numenter": 76, "numequal": 81, "numclear": 71,
}

VK = {**LETTERS, **DIGITS, **FKEYS, **PUNCT, **CONTROL, **NAV, **KEYPAD}
BY_CODE = {v: k for k, v in VK.items()}

MODS = ("cmd", "shift", "alt", "ctrl")

# ── display ─────────────────────────────────────────────────────────────
SYMBOL = {
    "cmd": "⌘", "shift": "⇧", "alt": "⌥", "ctrl": "⌃",
    "enter": "↩", "tab": "⇥", "space": "␣", "backspace": "⌫", "delete": "⌦",
    "esc": "⎋", "left": "←", "right": "→", "up": "↑", "down": "↓",
    "home": "↖", "end": "↘", "pageup": "⇞", "pagedown": "⇟",
    "minus": "−", "equal": "=", "grave": "`", "lbracket": "[", "rbracket": "]",
    "semicolon": ";", "quote": "'", "comma": ",", "dot": ".", "slash": "/",
    "backslash": "\\",
}

# Groups for the key picker in the interface
CATEGORIES = [
    ("letters", "Letters", "Bokstaver", sorted(LETTERS)),
    ("digits", "Numbers", "Tall", [str(d) for d in range(10)]),
    ("fkeys", "Function", "Funksjon", [f"f{i}" for i in range(1, 21)]),
    ("nav", "Navigation", "Navigasjon",
     ["left", "right", "up", "down", "home", "end", "pageup", "pagedown"]),
    ("control", "Control", "Kontroll",
     ["enter", "tab", "space", "backspace", "delete", "esc", "help"]),
    ("punct", "Punctuation", "Tegn", sorted(PUNCT)),
    ("keypad", "Keypad", "Talltastatur", sorted(KEYPAD)),
]


def display(spec: str) -> str:
    """'cmd+shift+equal' -> '⌘ ⇧ ='"""
    out = []
    for p in spec.split("+"):
        p = p.strip().lower()
        out.append(SYMBOL.get(p, p.upper() if len(p) == 1 else p.capitalize()))
    return " ".join(out)


def from_event(keycode: int, flags: int, masks: dict) -> str | None:
    """Convert an actual key press to binding text. Return None for modifier-only
    presses, which have no meaning on their own."""
    name = BY_CODE.get(keycode)
    if not name:
        return None
    parts = [m for m in MODS if flags & masks[m]]
    parts.append(name)
    return "+".join(parts)


def valid(spec: str) -> bool:
    parts = [p.strip().lower() for p in spec.split("+")]
    return bool(parts) and parts[-1] in VK and all(m in MODS for m in parts[:-1])
