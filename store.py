#!/usr/bin/env python3
"""
Profile store — the single source of truth for profiles.yaml.

Both the configurator (app.py) and daemon (daemon.py) read the same file, so the
schema must be defined in one place. Otherwise, they drift apart.

Schema:

    active: "Profile 1"
    profiles:
      "Profile 1": {default: {...}, apps: {...}}
      "Profile 2": {default: {},    apps: {}}
      "Profile 3": {default: {},    apps: {}}

Each profile is a complete set: a default profile plus app overrides. Switch the
active profile in the menu bar; the daemon dispatches from the active one.

The legacy format ({default, apps} at the top level) migrates to “Profile 1” on load.
"""
import yaml

import paths

# Fixed v1 names — three profiles, always present.
NAMES = ["Profile 1", "Profile 2", "Profile 3"]
LEGACY_NAMES = {"Profil 1": "Profile 1", "Profil 2": "Profile 2", "Profil 3": "Profile 3"}


def _blank():
    return {"default": {}, "apps": {}}


def normalize(doc):
    """Enforce a valid schema. Idempotent — safe to run on any input."""
    doc = doc or {}

    # Migrate the legacy single-profile format: {default, apps} without "profiles".
    if "profiles" not in doc:
        legacy = {"default": doc.get("default") or {},
                  "apps": doc.get("apps") or {}}
        doc = {"active": NAMES[0], "profiles": {NAMES[0]: legacy}}

    profs = doc.get("profiles") or {}
    for legacy, current in LEGACY_NAMES.items():
        if legacy in profs and current not in profs:
            profs[current] = profs.pop(legacy)
        if doc.get("active") == legacy:
            doc["active"] = current
    # Ensure all three profiles exist.
    for name in NAMES:
        profs.setdefault(name, _blank())
    # Ensure default+apps in each profile.
    for prof in profs.values():
        prof.setdefault("default", {})
        prof.setdefault("apps", {})
    doc["profiles"] = profs

    # active must point to an existing profile.
    if doc.get("active") not in profs:
        doc["active"] = NAMES[0]
    return doc


def load():
    """Read normalized profiles.yaml. Create it from the example when necessary."""
    path = paths.ensure_profiles()
    with open(path) as f:
        doc = yaml.safe_load(f) or {}
    return normalize(doc)


def save(doc):
    """Write normalized document to disk. Return the written document."""
    doc = normalize(doc)
    with open(paths.PROFILES, "w") as f:
        # profiles before active is harder to read; keep active first.
        ordered = {"active": doc["active"], "profiles": doc["profiles"]}
        yaml.safe_dump(ordered, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False)
    return doc


def active_map(doc):
    """Return {default, apps} for the active profile."""
    doc = normalize(doc)
    return doc["profiles"][doc["active"]]


def set_active(name):
    """Change the active profile on disk. Ignore unknown names and return the document."""
    doc = load()
    if name in doc["profiles"]:
        doc["active"] = name
        doc = save(doc)
    return doc
