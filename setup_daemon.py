#!/usr/bin/env python3
"""
Prepare the pad for the daemon: flash all 24 targets with unique signals.

Do this once. Afterwards, profiles.yaml controls everything — the pad never needs
to be reflashed when you change what keys do.

    .venv/bin/python setup_daemon.py          # flash
    .venv/bin/python setup_daemon.py --dry    # only show what would happen
"""
import sys

import signals
import xzkj


def build(target):
    """Signal specification -> (delay, code) entries for the protocol."""
    parts = signals.spec_for(target).split("+")
    mods, key = parts[:-1], parts[-1]
    entries = [(0, xzkj.MODIFIERS[m]) for m in mods]
    entries.append((0, xzkj.HID_CODES[key]))
    return entries


def main():
    dry = "--dry" in sys.argv
    plan = [(t, signals.key_id_for(t), signals.spec_for(t), build(t))
            for t in signals.TARGETS]

    for t, kid, spec, entries in plan:
        print(f"  {t:16s}  id {kid:2d}  ->  {spec:26s} ({len(entries)} presses)")
    if dry:
        print(f"\n{len(plan)} bindings — nothing written (--dry).")
        return

    h = xzkj.open_vendor_interface()
    try:
        for _, kid, _, entries in plan:
            xzkj.bind_key_sequence(h, kid, entries, layer=1)
        xzkj.finish(h)
    finally:
        h.close()
    print(f"\n{len(plan)} signals written to the pad.")
    print("Start the daemon:  .venv/bin/python daemon.py")


if __name__ == "__main__":
    main()
