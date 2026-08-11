#!/usr/bin/env python3
"""
Log exactly what macOS receives from the pad — listen only; swallow nothing.

    .venv/bin/python research/sniff_tap.py [seconds]

Requires Accessibility permission for the application running it (the same as the daemon).
"""
import sys
import time

import Quartz

SECS = int(sys.argv[1]) if len(sys.argv) > 1 else 20

VK = {105:"F13",107:"F14",113:"F15",106:"F16",64:"F17",79:"F18",80:"F19",90:"F20",
      57:"CAPSLOCK", 122:"F1",120:"F2",99:"F3",118:"F4",96:"F5",97:"F6",98:"F7",
      100:"F8",101:"F9",109:"F10",103:"F11",111:"F12",
      0:"A",11:"B",8:"C",2:"D",14:"E",3:"F",5:"G",4:"H",34:"I",38:"J",40:"K",37:"L",
      46:"M",45:"N",31:"O",35:"P",12:"Q",15:"R",1:"S",17:"T",32:"U",9:"V",13:"W",
      7:"X",16:"Y",6:"Z"}
FLAGS = [(Quartz.kCGEventFlagMaskCommand,"cmd"), (Quartz.kCGEventFlagMaskShift,"shift"),
         (Quartz.kCGEventFlagMaskAlternate,"alt"), (Quartz.kCGEventFlagMaskControl,"ctrl"),
         (Quartz.kCGEventFlagMaskAlphaShift,"CAPS-ON")]
TYPES = {Quartz.kCGEventKeyDown:"down", Quartz.kCGEventKeyUp:"up",
         Quartz.kCGEventFlagsChanged:"modifier"}


def cb(proxy, etype, event, refcon):
    if etype in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
        Quartz.CGEventTapEnable(tap, True)
        return event
    kc = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
    fl = Quartz.CGEventGetFlags(event)
    mods = "+".join(n for m, n in FLAGS if fl & m) or "-"
    print(f"  {TYPES.get(etype,etype):9s} keycode={kc:<4d} {VK.get(kc,'?'):9s} "
          f"flags={mods}", flush=True)
    return event


mask = (Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown) |
        Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp) |
        Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged))
tap = Quartz.CGEventTapCreate(Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
                              Quartz.kCGEventTapOptionListenOnly, mask, cb, None)
if not tap:
    print("Could not create event tap — Accessibility permission is missing.\n"
          "System Settings → Privacy & Security → Accessibility →\n"
          "add Terminal (or the application you are running this from).")
    raise SystemExit(1)

src = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), src, Quartz.kCFRunLoopCommonModes)
Quartz.CGEventTapEnable(tap, True)
print(f"Listening for {SECS}s. Use the pad now.\n", flush=True)
end = time.time() + SECS
while time.time() < end:
    Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 0.25, False)
print("\nDone.")
