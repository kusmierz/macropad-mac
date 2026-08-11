#!/usr/bin/env python3
"""
Device model for the XZKJ macropad — numbering follows the physical device:

    Knobs:  1 (small, upper left)  2 (small, lower left)  3 (medium)  4 (large)
    Keys:   5  6  7        (row 1, top)
            8  9 10        (row 2)
           11 12 13        (row 3)
           14 15 16        (row 4, bottom)

All key IDs are mapped empirically to the physical device.
"""

# knob number -> (left, press, right)
KNOB_IDS = {1: (19, 20, 21), 2: (16, 17, 18), 3: (22, 23, 24), 4: (13, 14, 15)}

# key number (5-16) -> key ID. The device counts bottom-to-top, by column.
KEY_IDS = {
    5: 4, 6: 8, 7: 12,
    8: 3, 9: 7, 10: 11,
    11: 2, 12: 6, 13: 10,
    14: 1, 15: 5, 16: 9,
}

KNOB_SIZES = {1: "small", 2: "small", 3: "medium", 4: "large"}
ACTIONS = ("left", "press", "right")
ACTION_LABELS = {"left": "turn left", "press": "press", "right": "turn right"}


def all_targets():
    """Return (target key, key ID, description) for every bindable control."""
    out = []
    for n in sorted(KNOB_IDS):
        for i, act in enumerate(ACTIONS):
            out.append((f"knob{n}.{act}", KNOB_IDS[n][i],
                        f"Knob {n} ({KNOB_SIZES[n]}) — {ACTION_LABELS[act]}"))
    for n in sorted(KEY_IDS):
        out.append((f"key{n}", KEY_IDS[n], f"Key {n}"))
    return out


def resolve(target: str) -> int:
    """'knob3.left' | 'key7' -> key-ID."""
    if target.startswith("knob"):
        num, act = target[4:].split(".")
        return KNOB_IDS[int(num)][ACTIONS.index(act)]
    if target.startswith("key"):
        return KEY_IDS[int(target[3:])]
    raise ValueError(f"Unknown target: {target!r}")
