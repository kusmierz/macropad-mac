#!/usr/bin/env python3
"""
File locations.

When the app runs from a .app bundle, its code is read-only, so the user's
configuration cannot sit beside it. It belongs in
~/Library/Application Support/Makropad/.

When running from source (development), use the project directory so the files
are easy to find while working.
"""
import os
import shutil
import sys

FROZEN = getattr(sys, "frozen", False)
BUNDLE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

if FROZEN:
    DATA = os.path.expanduser("~/Library/Application Support/Makropad")
else:
    DATA = os.path.dirname(os.path.abspath(__file__))

PROFILES = os.path.join(DATA, "profiles.yaml")
EXAMPLE = os.path.join(BUNDLE, "profiles.example.yaml")


def resource(name):
    """A file bundled with the application (ui.html, icons, example profile)."""
    p = os.path.join(BUNDLE, name)
    return p if os.path.exists(p) else None


def ensure_profiles():
    """Ensure a profiles.yaml exists to work with. Return its path."""
    os.makedirs(DATA, exist_ok=True)
    if not os.path.exists(PROFILES) and os.path.exists(EXAMPLE):
        shutil.copy(EXAMPLE, PROFILES)
    return PROFILES
