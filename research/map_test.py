#!/usr/bin/env python3
"""Mapping test: program IDs 1–24 to type their own number followed by a space."""
import xzkj

DIGIT = {str(d): xzkj.HID_CODES[str(d)] for d in range(10)}
SPACE = xzkj.HID_CODES["space"]

h = xzkj.open_vendor_interface()
try:
    for key_id in range(1, 25):
        s = f"{key_id:02d}"
        entries = [(0, DIGIT[c]) for c in s] + [(0, SPACE)]
        xzkj.bind_key_sequence(h, key_id, entries, layer=1)
        print(f"ID {key_id:2d} -> '{s} '")
    xzkj.finish(h)
    print("Done. Press every key and turn/press every knob in a text field.")
finally:
    h.close()
