#!/usr/bin/env python3
"""
Profile store - the single source of truth for profiles.yaml.

Both the configurator (app.py) and daemon (daemon.py) read the same file, so the
schema must be defined in one place. Otherwise, they drift apart.

Profiles are stored independently per device model:

    active_model: xzkj_12key_4knob
    models:
      xzkj_12key_4knob:
        active: "Profile 1"
        profiles:
          "Profile 1": {default: {...}, apps: {...}}
          "Profile 2": {default: {},    apps: {}}
          "Profile 3": {default: {},    apps: {}}

The legacy format ({default, apps} at the top level, or the former {active,
profiles} document) migrates to Profile 1 for the original 12-key/4-knob model.
"""
import os

import yaml

import device
import paths


NAMES = ["Profile 1", "Profile 2", "Profile 3"]
LEGACY_NAMES = {"Profil 1": "Profile 1", "Profil 2": "Profile 2", "Profil 3": "Profile 3"}


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
    for legacy, current in LEGACY_NAMES.items():
        if legacy in profiles and current not in profiles:
            profiles[current] = profiles.pop(legacy)
        if doc.get("active") == legacy:
            doc["active"] = current

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
    """Read normalized profiles.yaml. Create it from the example when necessary."""
    existed = os.path.exists(paths.PROFILES)
    path = paths.ensure_profiles()
    with open(path) as f:
        return normalize(yaml.safe_load(f) or {}, fresh=not existed)


def save(doc):
    """Write normalized document to disk. Return the written document."""
    doc = normalize(doc)
    with open(paths.PROFILES, "w") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return doc


def active_model(doc):
    return normalize(doc)["active_model"]


def model_doc(doc, model_id=None):
    doc = normalize(doc)
    selected = model_id if model_id is not None else doc["active_model"]
    if selected not in device.MODELS:
        raise ValueError(f"Unknown device model: {selected!r}")
    return doc["models"][selected]


def active_map(doc):
    """Return {default, apps} for the active profile of the active model."""
    selected = model_doc(doc)
    return selected["profiles"][selected["active"]]


def set_active(name):
    """Change the active profile on disk. Ignore unknown names and return the document."""
    doc = load()
    selected = model_doc(doc)
    if name in selected["profiles"]:
        selected["active"] = name
        doc = save(doc)
    return doc


def set_model(model_id):
    """Change the active device model on disk and return the document."""
    doc = load()
    if model_id not in device.MODELS:
        raise ValueError(f"Unknown device model: {model_id!r}")
    doc["active_model"] = model_id
    return save(doc)
