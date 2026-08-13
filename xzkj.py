#!/usr/bin/env python3
"""
Protocol library for the XZKJ macropad (VID 0x514C, PID 0x8850).

Protocol (reverse-engineered; see kriomant/ch57x-keyboard-tool issue #153):
  65-byte HID output reports on the vendor interface (usage page 0xFF00).

  Key binding (type 0x01 = keyboard):
    [0x03, 0xFD, key_id, layer, 0x01, 0x00, count,
     (delay_hi, delay_lo, hid_code) * count, ... zero-padded to 65]

  Modifiers are separate codes in the sequence and apply to the next regular key:
    0xF1 LCtrl  0xF2 LShift  0xF3 LAlt  0xF4 LMeta(Cmd)
    0xF5 RCtrl  0xF6 RShift  0xF7 RAlt  0xF8 RMeta
"""
import time
import hid

VID, PID = 0x514C, 0x8850
REPORT_LEN = 65  # including report ID 0x03
LED_COUNT = 16
LED_PALETTE_LEN = LED_COUNT * 3

MODIFIERS = {
    "lctrl": 0xF1, "ctrl": 0xF1,
    "lshift": 0xF2, "shift": 0xF2,
    "lalt": 0xF3, "alt": 0xF3, "opt": 0xF3, "option": 0xF3,
    "lmeta": 0xF4, "meta": 0xF4, "cmd": 0xF4, "win": 0xF4,
    "rctrl": 0xF5, "rshift": 0xF6, "ralt": 0xF7, "rmeta": 0xF8, "rcmd": 0xF8,
}

# HID Usage IDs (Keyboard/Keypad page)
HID_CODES = {
    **{chr(ord('a') + i): 0x04 + i for i in range(26)},
    **{str(d): 0x1E + d - 1 for d in range(1, 10)},
    "0": 0x27,
    "enter": 0x28, "esc": 0x29, "backspace": 0x2A, "tab": 0x2B, "space": 0x2C,
    "minus": 0x2D, "equal": 0x2E, "lbracket": 0x2F, "rbracket": 0x30,
    "backslash": 0x31, "semicolon": 0x33, "quote": 0x34, "grave": 0x35,
    "comma": 0x36, "dot": 0x37, "slash": 0x38, "capslock": 0x39,
    **{f"f{i}": 0x3A + i - 1 for i in range(1, 13)},
    **{f"f{i}": 0x68 + i - 13 for i in range(13, 25)},
    "printscreen": 0x46, "scrolllock": 0x47, "pause": 0x48,
    "insert": 0x49, "home": 0x4A, "pageup": 0x4B,
    "delete": 0x4C, "end": 0x4D, "pagedown": 0x4E,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
    # Media via keyboard usage page, verified on this device:
    "mute": 0x7F, "volumeup": 0x80, "volumedown": 0x81,
}

# Media/consumer codes (type 0x02; see k884x: 16-bit little-endian)
MEDIA_CODES = {
    "play": 0xCD, "playpause": 0xCD, "next": 0xB5, "prev": 0xB6, "stop": 0xB7,
    "mute": 0xE2, "volumeup": 0xE9, "volumedown": 0xEA,
    "brightnessup": 0x6F, "brightnessdown": 0x70,
    "calculator": 0x192, "browser": 0x196, "mail": 0x18A,
}


def open_vendor_interface():
    devs = [d for d in hid.enumerate(VID, PID) if d["usage_page"] == 0xFF00]
    if not devs:
        raise RuntimeError("Could not find the vendor interface (0xFF00). Is the keyboard connected?")
    h = hid.device()
    h.open_path(devs[0]["path"])
    return h


def _send(h, msg: bytes):
    buf = bytearray(REPORT_LEN)
    buf[: len(msg)] = msg
    n = h.write(bytes(buf))
    if n not in (REPORT_LEN, REPORT_LEN - 1):
        raise RuntimeError(f"Short write: {n} bytes")
    time.sleep(0.02)


def write_leds(h, mode: int, palette: bytes, layers=range(3)):
    """Write a 16-color RGB palette and mode to the selected LED layers."""
    if not 0 <= mode <= 5:
        raise ValueError("LED mode must be between 0 and 5")
    palette = bytes(palette)
    if len(palette) != LED_PALETTE_LEN:
        raise ValueError(f"LED palette must be exactly {LED_PALETTE_LEN} bytes")
    layers = tuple(layers)
    if any(not 0 <= layer <= 2 for layer in layers):
        raise ValueError("LED layer must be between 0 and 2")
    for layer in layers:
        _send(h, bytes([0x03, 0xFE, 0xB0, layer, mode]) + palette)


def write_led_color(h, red: int, green: int, blue: int, mode: int = 1):
    """Set all LEDs on all layers to one RGB color (mode 1 is static)."""
    channels = (red, green, blue)
    if any(not 0 <= channel <= 255 for channel in channels):
        raise ValueError("RGB channels must be between 0 and 255")
    write_leds(h, mode, bytes(channels) * LED_COUNT)


def bind_key_sequence(h, key_id: int, entries, layer: int = 1):
    """entries: a list of (delay_ms, hid_code). Maximum 18."""
    assert 1 <= len(entries) <= 18, "1-18 key presses per binding"
    msg = bytearray([0x03, 0xFD, key_id, layer, 0x01, 0x00, len(entries)])
    for delay_ms, code in entries:
        msg += bytes([(delay_ms >> 8) & 0xFF, delay_ms & 0xFF, code])
    _send(h, bytes(msg))


def bind_media(h, key_id: int, media_code: int, layer: int = 1, protocol="12_4"):
    """Media/consumer binding. The 16/3 model uses its captured frame layout."""
    lo, hi = media_code & 0xFF, (media_code >> 8) & 0xFF
    if protocol == "16_3":
        _send(h, bytes([0x03, 0xFD, key_id, layer, 0x02, 0x00, 0x02,
                        0x00, 0x00, lo, 0x00, 0x00, hi]))
        return
    _send(h, bytes([0x03, 0xFD, key_id, layer, 0x02, 0x00, 0x00, lo, hi]))


def bind_mouse_click(h, key_id: int, buttons: int = 1, layer: int = 1, protocol="12_4"):
    """Mouse binding (type 0x03), button bitmask: 1=left, 2=right, 4=middle."""
    if protocol == "16_3":
        mouse_data = bytearray([1, 4] + [0] * 15)
        mouse_data[7] = buttons
        _send(h, bytes([0x03, 0xFD, key_id, layer, 0x03]) + mouse_data)
        return
    _send(h, bytes([0x03, 0xFD, key_id, layer, 0x03, 0x00, 0x01, 0x00, buttons]))


def finish(h):
    """Finish the programming sequence (from k884x; unverified for 8850)."""
    _send(h, bytes([0x03, 0xAA, 0xAA]))
    _send(h, bytes([0x03, 0xFD, 0xFE, 0xFF]))
    _send(h, bytes([0x03, 0xAA, 0xAA]))
