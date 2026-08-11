#!/usr/bin/env python3
"""
Prepare the pad for the daemon: flash every target with a unique signal.

Do this once. Afterwards, profiles.yaml controls everything — the pad never needs
to be reflashed when you change what keys do.

    .venv/bin/python setup_daemon.py          # flash
    .venv/bin/python setup_daemon.py --dry    # only show what would happen
"""
import sys

import device
import signals
import store
import xzkj


def build(target, model_id=None):
    """Signal specification -> (delay, code) entries for the protocol."""
    parts = signals.spec_for(target, model_id).split("+")
    mods, key = parts[:-1], parts[-1]
    entries = [(0, xzkj.MODIFIERS[m]) for m in mods]
    entries.append((0, xzkj.HID_CODES[key]))
    return entries


def main():
    dry = "--dry" in sys.argv
    model_id = None
    if "--model" in sys.argv:
        try:
            model_id = sys.argv[sys.argv.index("--model") + 1]
        except IndexError:
            raise SystemExit("--model requires a model ID")
    if model_id is None:
        model_id = store.active_model(store.load())
    if model_id is None:
        raise SystemExit("Choose a device model in the configurator or use --model")
    model = device.get(model_id)
    plan = [(t, signals.key_id_for(t, model_id), signals.spec_for(t, model_id), build(t, model_id))
            for t in signals.targets(model_id)]

    for t, kid, spec, entries in plan:
        print(f"  {t:16s}  id {kid:2d}  ->  {spec:26s} ({len(entries)} presses)")
    if dry:
        print(f"\n{len(plan)} bindings for {model.name} — nothing written (--dry).")
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
