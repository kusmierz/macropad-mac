#!/usr/bin/env python3
"""
Klargjør padden for daemonen: flash alle 24 mål til hvert sitt signal.

Dette gjøres én gang. Etterpå styres alt fra profiles.yaml — padden trenger aldri
reflashes selv om du endrer hva tastene gjør.

    .venv/bin/python setup_daemon.py          # flash
    .venv/bin/python setup_daemon.py --dry    # bare vis hva som ville skjedd
"""
import sys

import device
import signals
import store
import xzkj


def build(target, model_id=None):
    """Signalspesifikasjon -> (delay, kode)-oppføringer for protokollen."""
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
            raise SystemExit("--model trenger en modell-ID")
    if model_id is None:
        model_id = store.active_model(store.load())
    if model_id is None:
        raise SystemExit("Velg enhetsmodell i konfiguratoren eller bruk --model")
    model = device.get(model_id)
    plan = [(t, signals.key_id_for(t, model_id), signals.spec_for(t, model_id), build(t, model_id))
            for t in signals.targets(model_id)]

    for t, kid, spec, entries in plan:
        print(f"  {t:16s}  id {kid:2d}  ->  {spec:26s} ({len(entries)} trykk)")
    if dry:
        print(f"\n{len(plan)} bindinger for {model.name} — ingenting skrevet (--dry).")
        return

    h = xzkj.open_vendor_interface()
    try:
        for _, kid, _, entries in plan:
            xzkj.bind_key_sequence(h, kid, entries, layer=1)
        xzkj.finish(h)
    finally:
        h.close()
    print(f"\n{len(plan)} signaler skrevet til padden.")
    print("Start daemonen:  .venv/bin/python daemon.py")


if __name__ == "__main__":
    main()
