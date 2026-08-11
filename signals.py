#!/usr/bin/env python3
"""Unique keyboard signals used to bridge a pad to the daemon."""
import device


FKEYS = [f"f{i}" for i in range(13, 21)]
# Keep the original three tiers unchanged. The fourth is needed only by the
# 25th target on the 16-key/3-knob model; do not use Hyper here.
TIERS = ["", "ctrl+alt+", "ctrl+shift+", "alt+shift+"]


def targets(model_id: str | None = None):
    return device.get(model_id).targets()


def signal_map(model_id: str | None = None):
    model_targets = targets(model_id)
    if len(model_targets) > len(FKEYS) * len(TIERS):
        raise ValueError("for mange mål for tilgjengelige signaler")
    return {target: TIERS[index // len(FKEYS)] + FKEYS[index % len(FKEYS)]
            for index, target in enumerate(model_targets)}


def reverse_signal_map(model_id: str | None = None):
    result = signal_map(model_id)
    reverse = {value: key for key, value in result.items()}
    assert len(result) == len(reverse), "signalene må være unike"
    return reverse


def spec_for(target: str, model_id: str | None = None) -> str:
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
