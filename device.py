#!/usr/bin/env python3
"""Models supported by the XZKJ macropad configurator."""
from dataclasses import dataclass


ACTIONS = ("left", "press", "right")
ACTION_LABELS = {"left": "turn left", "press": "press", "right": "turn right"}

MODEL_12_4 = "xzkj_12key_4knob"
MODEL_16_3 = "xzkj_16key_3knob"
DEFAULT_MODEL = MODEL_12_4


@dataclass(frozen=True)
class Model:
    id: str
    name: str
    board_id: str
    rows: int
    columns: int
    key_ids: dict
    knob_ids: dict
    knob_sizes: dict
    protocol: str
    ui: dict

    def targets(self):
        return [f"key{n}" for n in self.key_ids] + [
            f"knob{n}.{action}"
            for n in self.knob_ids
            for action in ACTIONS
        ]

    def resolve(self, target: str) -> int:
        if target.startswith("knob"):
            number, action = target[4:].split(".", 1)
            return self.knob_ids[int(number)][ACTIONS.index(action)]
        if target.startswith("key"):
            return self.key_ids[int(target[3:])]
        raise ValueError(f"Unknown target: {target!r}")


MODELS = {
    MODEL_12_4: Model(
        id=MODEL_12_4,
        name="XZKJ 12-key / 4-knob",
        board_id="@XZKJ-12key_4knob",
        rows=4,
        columns=3,
        key_ids={
            5: 4, 6: 8, 7: 12,
            8: 3, 9: 7, 10: 11,
            11: 2, 12: 6, 13: 10,
            14: 1, 15: 5, 16: 9,
        },
        knob_ids={1: (19, 20, 21), 2: (16, 17, 18), 3: (22, 23, 24), 4: (13, 14, 15)},
        knob_sizes={1: "small", 2: "small", 3: "medium", 4: "large"},
        protocol="12_4",
        ui={"shape": "lobe", "knobs": ["small", "small", "medium", "large"]},
    ),
    MODEL_16_3: Model(
        id=MODEL_16_3,
        name="XZKJ 16-key / 3-knob",
        board_id="@XZKJ-16key_3knob",
        rows=4,
        columns=4,
        key_ids={n: n for n in range(1, 17)},
        knob_ids={1: (17, 18, 19), 2: (20, 21, 22), 3: (23, 24, 25)},
        knob_sizes={1: "small", 2: "small", 3: "large"},
        protocol="16_3",
        ui={"shape": "rectangle", "knobs": ["small", "small", "large"]},
    ),
}


def get(model_id: str | None = None) -> Model:
    try:
        return MODELS[model_id or DEFAULT_MODEL]
    except KeyError as exc:
        raise ValueError(f"Unknown device model: {model_id!r}") from exc


def all_targets(model_id: str | None = None):
    """Return ``(target, key_id, description)`` for a model."""
    model = get(model_id)
    out = []
    for n, ids in model.knob_ids.items():
        for index, action in enumerate(ACTIONS):
            size = model.knob_sizes[n]
            out.append((f"knob{n}.{action}", ids[index],
                        f"Knob {n} ({size}) - {ACTION_LABELS[action]}"))
    for n, key_id in model.key_ids.items():
        out.append((f"key{n}", key_id, f"Key {n}"))
    return out


def resolve(target: str, model_id: str | None = None) -> int:
    return get(model_id).resolve(target)


def public_models():
    """JSON-safe model metadata used by the configurator."""
    return [{
        "id": model.id,
        "name": model.name,
        "boardId": model.board_id,
        "rows": model.rows,
        "columns": model.columns,
        "keys": list(model.key_ids),
        "knobs": [{"number": number, "size": model.knob_sizes[number]}
                  for number in model.knob_ids],
        "ui": model.ui,
    } for model in MODELS.values()]
