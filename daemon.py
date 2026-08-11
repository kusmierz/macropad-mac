#!/usr/bin/env python3
"""
Daemon — makes the pad app-aware.

The pad sends signals (F13–F20, with and without modifiers). This process captures
them, checks the frontmost app, and runs the action from profiles.yaml. The signal
is swallowed so no other app sees F13.

Start:   .venv/bin/python daemon.py
Requires: System Settings → Privacy & Security → Accessibility
          (add the app you run this from — Terminal, iTerm, etc.)
"""
import os
import sys
import time

import Quartz
from AppKit import NSWorkspace

import actions
import keys
import paths
import signals
import store

PROFILES = paths.PROFILES

# Virtual key codes for F13–F20 (the only ones macOS defines)
VK_F = {105: "f13", 107: "f14", 113: "f15", 106: "f16",
        64: "f17", 79: "f18", 80: "f19", 90: "f20"}

CTRL = Quartz.kCGEventFlagMaskControl
SHIFT = Quartz.kCGEventFlagMaskShift
ALT = Quartz.kCGEventFlagMaskAlternate
CMD = Quartz.kCGEventFlagMaskCommand
ALL = CTRL | SHIFT | ALT | CMD

# Must mirror TIERS in signals.py. Order matters: most specific first.
TIERS = [(ALT | SHIFT, "alt+shift+"), (CTRL | ALT, "ctrl+alt+"),
         (CTRL | SHIFT, "ctrl+shift+"), (0, "")]


def signal_name(keycode, flags):
    """Translate a key press to its signals.py signal name, or None."""
    name = VK_F.get(keycode)
    if not name:
        return None
    held = flags & ALL
    for mask, prefix in TIERS:
        if held == mask:          # exact match — no extra modifiers
            return prefix + name
    return None


class Daemon:
    def __init__(self):
        self.profiles = {}
        self.model_id = None
        self.mtime = 0
        self.load()

    def load(self):
        try:
            self.profiles = store.load()      # normalized; migrates and creates the file
            self.model_id = store.active_model(self.profiles)
            self.mtime = os.path.getmtime(PROFILES)
            if not self.model_id:
                print("Choose a device model in the configurator before using the daemon.")
                return
            active = store.model_doc(self.profiles)["active"]
            m = store.active_map(self.profiles)
            apps = list((m.get("apps") or {}).keys())
            print(f"Active profile: {active} — default + {len(apps)} app override(s)"
                  + (f" ({', '.join(apps)})" if apps else ""))
        except FileNotFoundError:
            print(f"Could not find {PROFILES} — no bindings created.")
            self.profiles = store.normalize({})

    def maybe_reload(self):
        try:
            if os.path.getmtime(PROFILES) != self.mtime:
                self.load()
        except OSError:
            pass

    def action_for(self, target: str, bundle: str):
        if not self.model_id:
            return (None, None)
        m = store.active_map(self.profiles)   # active profile's {default, apps}
        apps = m.get("apps") or {}
        for pattern, mapping in apps.items():
            if pattern.lower() in bundle.lower() and target in (mapping or {}):
                return (mapping[target], pattern)
        default = m.get("default") or {}
        return (default.get(target), None)

    def handle(self, target: str):
        bundle = actions.frontmost()
        action, via = self.action_for(target, bundle)
        if not action:
            print(f"  {target}: no action for {bundle}")
            return
        label = f"[{via}]" if via else "[default]"
        print(f"  {target} {label} -> {action}")
        try:
            actions.run(action)
        except Exception as e:
            print(f"  ! error: {e}")

    def target_for_signal(self, signal: str | None):
        if not self.model_id or not signal:
            return None
        return signals.reverse_signal_map(self.model_id).get(signal)


MASKS = {"cmd": Quartz.kCGEventFlagMaskCommand,
         "shift": Quartz.kCGEventFlagMaskShift,
         "alt": Quartz.kCGEventFlagMaskAlternate,
         "ctrl": Quartz.kCGEventFlagMaskControl}

# Capture mode: the interface asks the user to press keys, then captures the next
# real key press. Doing this here rather than in the browser catches everything,
# including cmd+Q and cmd+W, which the browser would consume itself. Everything is
# swallowed while capture is active, so nothing leaks to the app behind it.
CAPTURE = {"on": False, "result": None}

# Most recent pad press — the interface highlights the control just used.
LAST = {"target": None, "at": 0.0}


def capture_start():
    CAPTURE.update(on=True, result=None)


def capture_stop():
    CAPTURE["on"] = False


def capture_result():
    return CAPTURE["result"]


def last_press():
    return {"target": LAST["target"], "age": time.time() - LAST["at"]}


def make_callback(d: Daemon):
    def cb(proxy, etype, event, refcon):
        if etype in (Quartz.kCGEventTapDisabledByTimeout,
                     Quartz.kCGEventTapDisabledByUserInput):
            Quartz.CGEventTapEnable(TAP, True)
            return event
        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        flags = Quartz.CGEventGetFlags(event)

        if CAPTURE["on"]:
            spec = keys.from_event(keycode, flags, MASKS)
            if spec:                # modifier-only presses return None — keep waiting
                CAPTURE.update(on=False, result=spec)
            return None             # swallow all input: capture must not type anything

        d.maybe_reload()
        target = d.target_for_signal(signal_name(keycode, flags))
        if not target:
            return event  # not our signal — pass it through
        LAST.update(target=target, at=time.time())
        d.handle(target)
        return None  # swallow the signal
    return cb


TAP = None
CALLBACK = None   # must stay alive: otherwise PyObjC garbage-collects it and
                  # the tap silently stops delivering events
SOURCE = None

NO_ACCESS = ("Could not create an event tap — Accessibility permission is missing.\n"
             "System Settings → Privacy & Security → Accessibility →\n"
             "add the application, enable it, and restart it.")


def install_tap(d: Daemon):
    """Create the tap and attach it to the already-running run loop.

    Returns True on success. Does not run the loop itself — main() does that here,
    or NSApplication does when running inside the menu-bar app.
    """
    global TAP, CALLBACK, SOURCE
    if TAP:
        return True
    CALLBACK = make_callback(d)
    mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
    TAP = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault, mask, CALLBACK, None)
    if not TAP:
        CALLBACK = None
        return False
    SOURCE = Quartz.CFMachPortCreateRunLoopSource(None, TAP, 0)
    Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), SOURCE,
                              Quartz.kCFRunLoopCommonModes)
    Quartz.CGEventTapEnable(TAP, True)
    return True


def can_tap() -> bool:
    """Check for Accessibility by creating and discarding an event tap."""
    if TAP:
        return True
    t = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionListenOnly,
        Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown), lambda *a: None, None)
    return bool(t)


def set_enabled(on: bool):
    if TAP:
        Quartz.CGEventTapEnable(TAP, bool(on))


def is_enabled() -> bool:
    return bool(TAP) and Quartz.CGEventTapIsEnabled(TAP)


def main():
    d = Daemon()
    if not install_tap(d):
        print(NO_ACCESS)
        sys.exit(1)
    print("Daemon is running. Press the pad. Ctrl+C to quit.\n")
    try:
        Quartz.CFRunLoopRun()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
