#!/usr/bin/env python3
"""Profile storage, with independent profiles for each pad model."""
import os

import yaml

import device
import paths


NAMES = ["Profil 1", "Profil 2", "Profil 3"]


def _blank_profile():
    return {"default": {}, "apps": {}}


def _normalize_profiles(doc):
    """Normalize one model's former {active, profiles} document."""
    doc = doc or {}
    if "profiles" not in doc:
        doc = {"active": NAMES[0], "profiles": {
            NAMES[0]: {"default": doc.get("default") or {}, "apps": doc.get("apps") or {}}
        }}
    profiles = doc.get("profiles") or {}
    for name in NAMES:
        profiles.setdefault(name, _blank_profile())
    for profile in profiles.values():
        profile.setdefault("default", {})
        profile.setdefault("apps", {})
    active = doc.get("active") if doc.get("active") in profiles else NAMES[0]
    return {"active": active, "profiles": profiles}


def normalize(doc, fresh=False):
    """Migrate old profile documents and guarantee the current schema."""
    doc = doc or {}
    if "models" not in doc:
        # All previously supported installations were the 12-key/4-knob model.
        doc = {"active_model": None if fresh else device.DEFAULT_MODEL,
               "models": {device.DEFAULT_MODEL: _normalize_profiles(doc)}}

    models = doc.get("models") or {}
    for model_id in device.MODELS:
        models[model_id] = _normalize_profiles(models.get(model_id))
    active_model = doc.get("active_model")
    if active_model is not None and active_model not in device.MODELS:
        active_model = device.DEFAULT_MODEL
    return {"active_model": active_model, "models": models}


def load():
    existed = os.path.exists(paths.PROFILES)
    path = paths.ensure_profiles()
    with open(path) as f:
        return normalize(yaml.safe_load(f) or {}, fresh=not existed)


def save(doc):
    doc = normalize(doc)
    with open(paths.PROFILES, "w") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return doc


def active_model(doc):
    return normalize(doc)["active_model"]


def model_doc(doc, model_id=None):
    doc = normalize(doc)
    selected = model_id or doc["active_model"]
    if selected not in device.MODELS:
        raise ValueError(f"Ukjent enhetsmodell: {selected!r}")
    return doc["models"][selected]


def active_map(doc):
    selected = model_doc(doc)
    return selected["profiles"][selected["active"]]


def set_active(name):
    doc = load()
    selected = model_doc(doc)
    if name in selected["profiles"]:
        selected["active"] = name
        doc = save(doc)
    return doc


def set_model(model_id):
    doc = load()
    if model_id not in device.MODELS:
        raise ValueError(f"Ukjent enhetsmodell: {model_id!r}")
    doc["active_model"] = model_id
    return save(doc)
