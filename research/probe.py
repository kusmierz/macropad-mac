#!/usr/bin/env python3
"""Probe: find and open the vendor HID interface on the XZKJ macropad (514C:8850)."""
import hid

VID, PID = 0x514C, 0x8850

devs = [d for d in hid.enumerate(VID, PID)]
if not devs:
    print("No 514C:8850 device found — is it connected?")
    raise SystemExit(1)

for d in devs:
    print(f"path={d['path'].decode()} usage_page={d['usage_page']:#06x} "
          f"usage={d['usage']:#04x} interface={d['interface_number']}")

vendor = [d for d in devs if d["usage_page"] == 0xFF00]
if not vendor:
    print("\nNo usage_page 0xFF00 found — trying the interface number instead.")
    raise SystemExit(2)

path = vendor[0]["path"]
print(f"\nOpening vendor interface: {path.decode()}")
h = hid.device()
h.open_path(path)
print("Opened successfully:", h.get_manufacturer_string(), "/", h.get_product_string())
h.close()
