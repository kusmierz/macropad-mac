#!/usr/bin/env python3
"""
macroctl — configurator for supported XZKJ macropads (514C:8850).

Usage:
    macroctl.py flash config.yaml     # write configuration to the keyboard
    macroctl.py validate config.yaml  # check configuration without writing
    macroctl.py list-keys             # list valid key names

Configuration format (YAML): see config.example.yaml.
Key specification:
    "cmd+c"                 chord (modifiers + key)
    "cmd+shift+4"           multiple modifiers
    "h,e,i"                 key-press sequence (maximum 18, including modifiers)
    "c@100"                 100 ms delay before the key press
    "media:volumeup"        media/consumer key
    "mouse:left"            mouse click (left/right/middle)
"""
import sys

import yaml

import device
import xzkj

def key_pos_to_id(row: int, col: int, model_id: str = device.DEFAULT_MODEL) -> int:
    """Return the selected model's ID for a visual row/column position."""
    model = device.get(model_id)
    index = (row - 1) * model.columns + (col - 1)
    return model.key_ids[list(model.key_ids)[index]]


def parse_binding(spec: str):
    """Return ('kbd', entries) | ('media', code) | ('mouse', buttons)."""
    spec = str(spec).strip().lower()
    if spec in ("", "none", "~"):
        return None

    if spec.startswith("media:"):
        name = spec[6:]
        if name not in xzkj.MEDIA_CODES:
            raise ValueError(f"Unknown media key: {name!r} (valid: {', '.join(xzkj.MEDIA_CODES)})")
        return ("media", xzkj.MEDIA_CODES[name])

    if spec.startswith("mouse:"):
        btn = {"left": 1, "right": 2, "middle": 4}.get(spec[6:])
        if btn is None:
            raise ValueError(f"Unknown mouse button: {spec[6:]!r} (left/right/middle)")
        return ("mouse", btn)

    entries = []
    for chord in spec.split(","):
        chord = chord.strip()
        delay = 0
        if "@" in chord:
            chord, d = chord.rsplit("@", 1)
            delay = int(d)
            if not 0 <= delay <= 65535:
                raise ValueError(f"Invalid delay: {delay}")
        parts = [p.strip() for p in chord.split("+")]
        mods, key = parts[:-1], parts[-1]
        for m in mods:
            if m not in xzkj.MODIFIERS:
                raise ValueError(f"Unknown modifier: {m!r}")
            entries.append((0, xzkj.MODIFIERS[m]))
        if key in xzkj.MODIFIERS:  # standalone modifier as the final element
            entries.append((delay, xzkj.MODIFIERS[key]))
        elif key in xzkj.HID_CODES:
            entries.append((delay, xzkj.HID_CODES[key]))
        else:
            raise ValueError(f"Unknown key: {key!r} (see 'macroctl.py list-keys')")
    if not 1 <= len(entries) <= 18:
        raise ValueError(f"Sequence has {len(entries)} key presses — maximum 18 (including modifiers)")
    return ("kbd", entries)


def load_config(path: str):
    with open(path) as f:
        cfg = yaml.safe_load(f)

    model_id = cfg.get("model", device.DEFAULT_MODEL)
    model = device.get(model_id)
    layer = int(cfg.get("layer", 1))
    bindings = []  # (key_id, description, parsed)

    rows = cfg.get("keys", [])
    if len(rows) != model.rows:
        raise ValueError(f"'keys' must have {model.rows} rows (has {len(rows)})")
    for r, row in enumerate(rows, 1):
        if len(row) != model.columns:
            raise ValueError(f"Row {r} must have {model.columns} columns (has {len(row)})")
        for c, spec in enumerate(row, 1):
            parsed = parse_binding(spec) if spec is not None else None
            if parsed:
                bindings.append((key_pos_to_id(r, c, model_id), f"key row{r}/col{c} = {spec!r}", parsed))

    for knob_no, actions in (cfg.get("knobs") or {}).items():
        knob_no = int(knob_no)
        if knob_no not in model.knob_ids:
            raise ValueError(f"Invalid knob: {knob_no}")
        ids = model.knob_ids[knob_no]
        for action, idx in (("left", 0), ("press", 1), ("right", 2)):
            spec = (actions or {}).get(action)
            if spec is not None:
                parsed = parse_binding(spec)
                if parsed:
                    bindings.append((ids[idx], f"knob {knob_no} {action} = {spec!r}", parsed))

    return model, layer, bindings


def flash(model, layer, bindings):
    h = xzkj.open_vendor_interface()
    try:
        for key_id, desc, (kind, val) in bindings:
            if kind == "kbd":
                xzkj.bind_key_sequence(h, key_id, val, layer)
            elif kind == "media":
                xzkj.bind_media(h, key_id, val, layer, model.protocol)
            elif kind == "mouse":
                xzkj.bind_mouse_click(h, key_id, val, layer, model.protocol)
            print(f"  ID {key_id:2d}  {desc}")
        xzkj.finish(h)
    finally:
        h.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]

    if cmd == "list-keys":
        print("Keys:", " ".join(sorted(xzkj.HID_CODES)))
        print("\nModifiers:", " ".join(sorted(set(xzkj.MODIFIERS))))
        print("\nMedia:", " ".join(sorted(xzkj.MEDIA_CODES)))
        return 0

    if cmd in ("flash", "validate") and len(sys.argv) == 3:
        model, layer, bindings = load_config(sys.argv[2])
        print(f"{model.name}, layer {layer}, {len(bindings)} bindings:")
        if cmd == "validate":
            for key_id, desc, _ in bindings:
                print(f"  ID {key_id:2d}  {desc}")
            print("OK — configuration is valid.")
        else:
            flash(model, layer, bindings)
            print("Written to the keyboard.")
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
