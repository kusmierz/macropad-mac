#!/usr/bin/env python3
"""
Signals - the bridge between the pad and daemon.

The pad knows nothing about the app in use; it only sends key presses. We bind each
physical key/knob to a signal: a combination that nothing else uses. The daemon
captures the signal and decides what should actually happen.

macOS has virtual key codes only for F13-F20 (eight). The original 12-key/4-knob
model needs 24 signals, so it uses three modifier tiers:

    tier 0:  F13-F20              (8)
    tier 1:  ctrl+alt + F13-F20   (8)
    tier 2:  ctrl+shift + F13-F20 (8)

The 16-key/3-knob model has a 25th target, so it uses one value from a fourth
non-Hyper tier.

F13-F20 do not exist on Mac keyboards, so they are safe to claim.

NOTE - do not use Hyper (cmd+ctrl+shift+alt). Tools such as Karabiner, SupaKey,
and TellyKeys use that stack for Caps Lock, causing Caps Lock to toggle whenever
you use the pad. Verified with research/sniff_tap.py. Two modifiers are enough and
collide far less often.
"""
import device


FKEYS = [f"f{i}" for i in range(13, 21)]
TIERS = ["", "ctrl+alt+", "ctrl+shift+", "alt+shift+"]


def targets(model_id: str | None = None):
    return device.get(model_id).targets()


def signal_map(model_id: str | None = None):
    model_targets = targets(model_id)
    if len(model_targets) > len(FKEYS) * len(TIERS):
        raise ValueError("too many targets for available signals")
    return {target: TIERS[index // len(FKEYS)] + FKEYS[index % len(FKEYS)]
            for index, target in enumerate(model_targets)}


def reverse_signal_map(model_id: str | None = None):
    result = signal_map(model_id)
    reverse = {value: key for key, value in result.items()}
    assert len(result) == len(reverse), "signals must be unique"
    return reverse


def spec_for(target: str, model_id: str | None = None) -> str:
    """Return the binding to flash to the pad for a given target."""
    return signal_map(model_id)[target]


def key_id_for(target: str, model_id: str | None = None) -> int:
    return device.resolve(target, model_id)


# Compatibility exports for callers and profiles targeting the original model.
TARGETS = targets()
SIGNALS = signal_map()
BY_SIGNAL = reverse_signal_map()


if __name__ == "__main__":
    for target in TARGETS:
        print(f"{target:16s}  id {key_id_for(target):2d}   ->  {spec_for(target)}")
