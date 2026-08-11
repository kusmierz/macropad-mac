#!/usr/bin/env python3
"""Round 2: identify the physical knobs and verify keyboard-page media codes."""
import xzkj

h = xzkj.open_vendor_interface()
K = xzkj.HID_CODES
try:
    # Knob 1 (ID 19/20/21): left=VolUp(0x80), press=types 'k1', right=VolDown(0x81)
    xzkj.bind_key_sequence(h, 19, [(0, 0x80)])
    xzkj.bind_key_sequence(h, 20, [(0, K["k"]), (0, K["1"])])
    xzkj.bind_key_sequence(h, 21, [(0, 0x81)])
    # Knob 2 (ID 16/17/18): left=Mute(0x7F), press=types 'k2', right=type2 entry E9
    xzkj.bind_key_sequence(h, 16, [(0, 0x7F)])
    xzkj.bind_key_sequence(h, 17, [(0, K["k"]), (0, K["2"])])
    xzkj._send(h, bytes([0x03, 0xFD, 18, 1, 0x02, 0x00, 0x01, 0x00, 0x00, 0xE9]))
    xzkj.finish(h)
    print("Flashed round 2.")
finally:
    h.close()
