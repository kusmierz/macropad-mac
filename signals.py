#!/usr/bin/env python3
"""
Signals — the bridge between the pad and daemon.

The pad knows nothing about the app in use; it only sends key presses. We bind each
physical key/knob to a *signal*: a combination that nothing else uses. The daemon
captures the signal and decides what should actually happen.

macOS has virtual key codes only for F13–F20 (eight). We need 24 signals
(12 keys + 4 knobs × 3), so we use three modifier tiers:

    tier 0:  F13–F20              (8)
    tier 1:  ctrl+alt + F13–F20   (8)
    tier 2:  ctrl+shift + F13–F20 (8)

F13–F20 do not exist on Mac keyboards, so they are safe to claim.

NOTE — do not use “hyper” (cmd+ctrl+shift+alt). Tools such as Karabiner, SupaKey,
and TellyKeys use that stack for Caps Lock, causing Caps Lock to toggle whenever
you use the pad. Verified with research/sniff_tap.py. Two modifiers are enough and
collide far less often.
"""
import device

FKEYS = [f"f{i}" for i in range(13, 21)]           # F13–F20
TIERS = ["", "ctrl+alt+", "ctrl+shift+"]

# All targets in physical order: 12 keys, then the knobs
TARGETS = [f"key{n}" for n in range(5, 17)] + \
          [f"knob{n}.{a}" for n in (1, 2, 3, 4) for a in ("left", "press", "right")]

SIGNALS = {t: TIERS[i // 8] + FKEYS[i % 8] for i, t in enumerate(TARGETS)}
BY_SIGNAL = {v: k for k, v in SIGNALS.items()}

assert len(SIGNALS) == 24 and len(BY_SIGNAL) == 24, "signals must be unique"


def spec_for(target: str) -> str:
    """The binding to flash to the pad for a given target."""
    return SIGNALS[target]


def key_id_for(target: str) -> int:
    return device.resolve(target)


if __name__ == "__main__":
    for t in TARGETS:
        print(f"{t:16s}  id {key_id_for(t):2d}   ->  {SIGNALS[t]}")
