#!/usr/bin/env python3
"""
Actions the daemon can run. Add new actions here.

Action syntax in profiles.yaml:
    media:playpause     media:next  media:prev  media:mute
    media:volumeup      media:volumedown
    key:cmd+shift+4     send a key combination
    app:Spotify         activate (or launch) an app
    url:https://…       open a URL
    shell:say hello     run a command
    none                do nothing (swallow the signal)
"""
import subprocess

import Quartz
from AppKit import NSWorkspace

import keys

# NX_KEYTYPE codes for the system media keys
NX = {
    "playpause": 16, "next": 17, "prev": 18, "fast": 19, "rewind": 20,
    "mute": 7, "volumeup": 0, "volumedown": 1,
    "brightnessup": 2, "brightnessdown": 3,
}

# Virtual key codes — shared map; see keys.py
VK = {**keys.VK, "period": keys.VK["dot"]}   # 'period' is a common alias

MODMASK = {
    "cmd": Quartz.kCGEventFlagMaskCommand,
    "shift": Quartz.kCGEventFlagMaskShift,
    "alt": Quartz.kCGEventFlagMaskAlternate,
    "opt": Quartz.kCGEventFlagMaskAlternate,
    "ctrl": Quartz.kCGEventFlagMaskControl,
}


def _media(name):
    code = NX.get(name)
    if code is None:
        raise ValueError(f"Unknown media action: {name}")
    for down in (True, False):
        data = (code << 16) | ((0xA if down else 0xB) << 8)
        ev = Quartz.NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            14, (0, 0), 0xA00 if down else 0xB00, 0, 0, None, 8, data, -1)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev.CGEvent())


def _key(spec):
    parts = [p.strip().lower() for p in spec.split("+")]
    mods, key = parts[:-1], parts[-1]
    if key not in VK:
        raise ValueError(f"Unknown key: {key}")
    flags = 0
    for m in mods:
        if m not in MODMASK:
            raise ValueError(f"Unknown modifier: {m}")
        flags |= MODMASK[m]
    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(None, VK[key], down)
        Quartz.CGEventSetFlags(ev, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def _app(name):
    NSWorkspace.sharedWorkspace().launchApplication_(name)


def run(action: str):
    """Run an action. Raises on invalid syntax."""
    action = (action or "").strip()
    if not action or action == "none":
        return
    if ":" not in action:
        raise ValueError(f"Action is missing a type: {action!r}")
    kind, arg = action.split(":", 1)
    kind, arg = kind.strip().lower(), arg.strip()
    if kind == "media":
        _media(arg.lower())
    elif kind == "key":
        _key(arg)
    elif kind == "app":
        _app(arg)
    elif kind == "url":
        subprocess.Popen(["open", arg])
    elif kind == "shell":
        subprocess.Popen(arg, shell=True)
    else:
        raise ValueError(f"Unknown action type: {kind!r}")


def validate(action: str):
    """Check syntax without running the action."""
    action = (action or "").strip()
    if not action or action == "none":
        return
    if ":" not in action:
        raise ValueError(f"Action is missing a type: {action!r}")
    kind, arg = action.split(":", 1)
    kind, arg = kind.strip().lower(), arg.strip()
    if kind == "media":
        if arg.lower() not in NX:
            raise ValueError(f"Unknown media action: {arg} (valid: {', '.join(NX)})")
    elif kind == "key":
        parts = [p.strip().lower() for p in arg.split("+")]
        if parts[-1] not in VK:
            raise ValueError(f"Unknown key: {parts[-1]}")
        for m in parts[:-1]:
            if m not in MODMASK:
                raise ValueError(f"Unknown modifier: {m}")
    elif kind not in ("app", "url", "shell"):
        raise ValueError(f"Unknown action type: {kind!r}")


def frontmost() -> str:
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return app.bundleIdentifier() or ""
