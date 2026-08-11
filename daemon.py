#!/usr/bin/env python3
"""
Daemon — gjør padden app-avhengig.

Padden sender signaler (F13–F24, med og uten hyper). Denne prosessen fanger dem,
sjekker hvilken app som er i front, og utfører handlingen fra profiles.yaml.
Signalet svelges, så ingen andre apper ser F13.

Start:   .venv/bin/python daemon.py
Krever:  Systeminnstillinger → Personvern og sikkerhet → Tilgjengelighet
         (legg til appen du kjører dette fra — Terminal, iTerm e.l.)
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

# Virtuelle tastekoder for F13–F20 (de eneste macOS definerer)
VK_F = {105: "f13", 107: "f14", 113: "f15", 106: "f16",
        64: "f17", 79: "f18", 80: "f19", 90: "f20"}

CTRL = Quartz.kCGEventFlagMaskControl
SHIFT = Quartz.kCGEventFlagMaskShift
ALT = Quartz.kCGEventFlagMaskAlternate
CMD = Quartz.kCGEventFlagMaskCommand
ALL = CTRL | SHIFT | ALT | CMD

# Må speile TIERS i signals.py. Rekkefølgen betyr noe: mest spesifikke først.
TIERS = [(ALT | SHIFT, "alt+shift+"), (CTRL | ALT, "ctrl+alt+"),
         (CTRL | SHIFT, "ctrl+shift+"), (0, "")]


def signal_name(keycode, flags):
    """Oversett et tastetrykk til signalnavnet i signals.py, eller None."""
    name = VK_F.get(keycode)
    if not name:
        return None
    held = flags & ALL
    for mask, prefix in TIERS:
        if held == mask:          # eksakt treff — ingen ekstra modifikatorer
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
            self.profiles = store.load()      # normalisert; migrerer + lager fila
            self.model_id = store.active_model(self.profiles)
            self.mtime = os.path.getmtime(PROFILES)
            if not self.model_id:
                print("Velg enhetsmodell i konfiguratoren før daemonen brukes.")
                return
            active = store.model_doc(self.profiles)["active"]
            m = store.active_map(self.profiles)
            apps = list((m.get("apps") or {}).keys())
            print(f"Aktiv profil: {active} — standard + {len(apps)} app-overstyring(er)"
                  + (f" ({', '.join(apps)})" if apps else ""))
        except FileNotFoundError:
            print(f"Fant ikke {PROFILES} — lager ingen bindinger.")
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
        m = store.active_map(self.profiles)   # aktiv profils {default, apps}
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
            print(f"  {target}: ingen handling for {bundle}")
            return
        label = f"[{via}]" if via else "[standard]"
        print(f"  {target} {label} -> {action}")
        try:
            actions.run(action)
        except Exception as e:
            print(f"  ! feil: {e}")

    def target_for_signal(self, signal: str | None):
        if not self.model_id or not signal:
            return None
        return signals.reverse_signal_map(self.model_id).get(signal)


MASKS = {"cmd": Quartz.kCGEventFlagMaskCommand,
         "shift": Quartz.kCGEventFlagMaskShift,
         "alt": Quartz.kCGEventFlagMaskAlternate,
         "ctrl": Quartz.kCGEventFlagMaskControl}

# Opptaksmodus: grensesnittet ber om «trykk tastene du vil ha», og vi fanger
# neste ekte tastetrykk. Fordelen med å gjøre det her framfor i nettleseren er
# at tapen ser alt — også cmd+Q og cmd+W, som nettleseren ville spist selv.
# Alt svelges mens opptaket står på, så ingenting lekker ut i appen bak.
CAPTURE = {"on": False, "result": None}

# Siste padde-trykk — grensesnittet lyser opp tasten du nettopp rørte.
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
            if spec:                # rene modifikatorer gir None — vent videre
                CAPTURE.update(on=False, result=spec)
            return None             # svelg alt: opptaket skal ikke skrive noe

        d.maybe_reload()
        target = d.target_for_signal(signal_name(keycode, flags))
        if not target:
            return event  # ikke vårt signal — la den passere
        LAST.update(target=target, at=time.time())
        d.handle(target)
        return None  # svelg signalet
    return cb


TAP = None
CALLBACK = None   # må holdes i live: PyObjC samler den ellers som søppel,
                  # og tapen slutter stille å levere hendelser
SOURCE = None

NO_ACCESS = ("Kunne ikke opprette event tap — mangler Tilgjengelighet-tilgang.\n"
             "Systeminnstillinger → Personvern og sikkerhet → Tilgjengelighet →\n"
             "legg til programmet, huk av, og start det på nytt.")


def install_tap(d: Daemon):
    """Opprett tapen og heng den på run-loopen som allerede kjører.

    Returnerer True om det gikk. Kaller ikke run-loopen selv — det gjør enten
    main() her, eller NSApplication når vi kjører inne i menylinje-appen.
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
    """Har prosessen Tilgjengelighet? Prøver å opprette en tap og kaster den."""
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
    print("Daemon kjører. Trykk på padden. Ctrl+C for å avslutte.\n")
    try:
        Quartz.CFRunLoopRun()
    except KeyboardInterrupt:
        print("\nAvsluttet.")


if __name__ == "__main__":
    main()
