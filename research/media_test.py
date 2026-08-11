#!/usr/bin/env python3
"""Test five media-binding hypotheses (volume up) on knobs 1 and 2."""
import xzkj

h = xzkj.open_vendor_interface()
send = lambda msg: xzkj._send(h, bytes(msg))

L = 1  # layer

# Knob 1: left=19 press=20 right=21 | Knob 2: left=16 press=17 right=18
tests = [
    ("H1 knob1-left: kbd-type, keyboard-page VolumeUp 0x80",
     [0x03, 0xFD, 19, L, 0x01, 0x00, 0x01, 0x00, 0x00, 0x80]),
    ("H2 knob1-press:    type2, count=1, 3-byte-entry [00 00 E9]",
     [0x03, 0xFD, 20, L, 0x02, 0x00, 0x01, 0x00, 0x00, 0xE9]),
    ("H3 knob1-right:    type2, count=1, code LE at offset 7-8",
     [0x03, 0xFD, 21, L, 0x02, 0x00, 0x01, 0xE9, 0x00]),
    ("H4 knob2-left:     type2, count=0, code LE at offset 7-8 (k884x style)",
     [0x03, 0xFD, 16, L, 0x02, 0x00, 0x00, 0xE9, 0x00]),
    ("H5 knob2-right:    type3 with offset5=2, 3-byte-entry",
     [0x03, 0xFD, 18, L, 0x03, 0x02, 0x01, 0x00, 0x00, 0xE9]),
]

try:
    for desc, msg in tests:
        send(msg)
        print(desc)
    xzkj.finish(h)
    print("\nFlashed. Test: turn knob 1 both ways and press it; turn knob 2 both ways.")
finally:
    h.close()
