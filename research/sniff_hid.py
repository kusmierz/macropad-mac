#!/usr/bin/env python3
"""
Read the raw HID reports sent by the pad to see what it actually does,
rather than inferring it from macOS behavior.

    .venv/bin/python research/sniff_hid.py [seconds]
"""
import sys
import time

import hid

VID, PID = 0x514C, 0x8850
SECS = int(sys.argv[1]) if len(sys.argv) > 1 else 15

# HID keyboard usage -> names we care about
NAMES = {0x39: "CAPSLOCK", 0x7F: "MUTE", 0x80: "VOL+", 0x81: "VOL-",
         **{0x3A + i: f"F{i+1}" for i in range(12)},
         **{0x68 + i: f"F{i+13}" for i in range(12)},
         **{0x04 + i: chr(ord('a') + i).upper() for i in range(26)}}
MODS = ["LCTRL", "LSHIFT", "LALT", "LMETA", "RCTRL", "RSHIFT", "RALT", "RMETA"]


def decode(d):
    if len(d) < 3:
        return " ".join(f"{b:02x}" for b in d)
    mods = [MODS[i] for i in range(8) if d[0] & (1 << i)]
    keys = [NAMES.get(b, f"0x{b:02x}") for b in d[2:] if b]
    return "+".join(mods + keys) if (mods or keys) else "(release)"


devs = [d for d in hid.enumerate(VID, PID) if d["usage_page"] != 0xFF00]
if not devs:
    print("No input interfaces found.")
    raise SystemExit(1)

opened = []
for d in devs:
    try:
        h = hid.device()
        h.open_path(d["path"])
        h.set_nonblocking(True)
        opened.append((d, h))
    except Exception as e:
        print(f"could not open usage_page={d['usage_page']:#06x}: {e}")

if not opened:
    print("Could not open any input interfaces.\n"
          "macOS may require Input Monitoring: System Settings → Privacy & Security\n"
          "→ Input Monitoring → add Terminal.")
    raise SystemExit(2)

print(f"Listening for {SECS}s on {len(opened)} interfaces. Use the pad now.\n", flush=True)
end = time.time() + SECS
seen = 0
while time.time() < end:
    for d, h in opened:
        try:
            data = h.read(64)
        except Exception:
            continue
        if data:
            seen += 1
            up = d["usage_page"]
            raw = " ".join(f"{b:02x}" for b in data[:8])
            print(f"  [up {up:#06x}]  {raw:24s}  {decode(data)}", flush=True)
    time.sleep(0.004)

for _, h in opened:
    h.close()
print(f"\nDone — {seen} reports.")
