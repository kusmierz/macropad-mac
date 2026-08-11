# Protocol — XZKJ macropads (514C:8850)

Reverse-engineered on macOS against a physical device, July 2026. Based on
[ch57x-keyboard-tool issue #153](https://github.com/kriomant/ch57x-keyboard-tool/issues/153),
which documented the `03 fd` frame for the 16-key/3-knob variant with the same VID/PID.

`514C:8850` identifies both supported layouts, not a single physical model. Select the model
explicitly before writing bindings.

## Transport

USB HID, vendor interface (usage page `0xFF00`, interface 0). The device also exposes
standard HID interfaces (keyboard/mouse/consumer) on interface 1 — they are for input only.

```python
devs = [d for d in hid.enumerate(0x514C, 0x8850) if d["usage_page"] == 0xFF00]
h = hid.device(); h.open_path(devs[0]["path"])
```

Output reports are **65 bytes**, including report ID `0x03`, zero-padded.

## Key bindings (type 0x01)

```
offset  0     1     2       3      4     5     6      7...
        0x03  0xFD  key_id  layer  0x01  0x00  count  (delay_hi, delay_lo, hid_code) × count
```

- `layer` is 1-based (1–3 on this device)
- `count` ≤ 18 — modifiers count toward the limit
- Each entry is 3 bytes: a 16-bit big-endian delay in ms, followed by the HID usage ID

Modifiers are separate codes in the sequence and apply to **the first non-modifier that
follows**:

| Code | Modifier | Code | Modifier |
|---|---|---|---|
| `0xF1` | Left Ctrl | `0xF5` | Right Ctrl |
| `0xF2` | Left Shift | `0xF6` | Right Shift |
| `0xF3` | Left Alt | `0xF7` | Right Alt |
| `0xF4` | Left Meta/Cmd | `0xF8` | Right Meta |

Example — `Ctrl+Alt+Delete` on key ID 1, layer 1:

```
03 fd 01 01 01 00 03  00 00 f1  00 00 f3  00 00 4c
```

## Mouse clicks (type 0x03)

```
03 fd key_id layer 03 00 01 00 buttons
```

`buttons` is a bitmask: `1` = left, `2` = right, `4` = middle.

## Media

**Finding for this variant:** volume and mute are on the **keyboard usage page**, not
the consumer page, and are bound as ordinary key codes with type `0x01`:

| Code | Function |
|---|---|
| `0x7F` | Mute |
| `0x80` | Volume up |
| `0x81` | Volume down |

The k884x-style consumer type (`0x02`) was tested in five variants and produced no response
on this device. Play/pause/next/previous therefore remain unresolved — they do not exist on
the keyboard page, so they must use a consumer format we have not yet found.

## Ending programming

```
03 aa aa
03 fd fe ff
03 aa aa
```

## Key ID map

### @XZKJ-16key_3knob

The 4×4/3-knob model is row-major: `key1` through `key16` map directly to IDs `1` through
`16`. Knob actions then occupy IDs `17–25`: knob 1 is `17–19`, knob 2 is `20–22`, and knob 3
is `23–25` (left, press, right). Its consumer-media and mouse frames use the captured upstream
16/3 format; keyboard bindings use the common frame documented above.

### @XZKJ-12key_4knob

The device counts keys **from bottom to top, column by column** — not in reading order. Mapped
empirically by binding each ID to type its own number.

Physical numbering (as in the software and the README illustration):

```
      (1)      (3)        ( 4 )
      (2)

       5    6    7
       8    9   10
      11   12   13
      14   15   16
```

Keys:

| Physical | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **key_id** | 4 | 8 | 12 | 3 | 7 | 11 | 2 | 6 | 10 | 1 | 5 | 9 |

Knobs — each provides three IDs:

| Knob | Turn left | Press | Turn right |
|---|---|---|---|
| 1 (small, upper left) | 19 | 20 | 21 |
| 2 (small, lower left) | 16 | 17 | 18 |
| 3 (medium) | 22 | 23 | 24 |
| 4 (large) | 13 | 14 | 15 |

Note that knob 4 uses IDs 13–15 — the range allocated to keys on 15-key/3-knob models.
The same observation was made in `k884x.rs` in ch57x-keyboard-tool: one row of keys is
effectively replaced by an extra knob. The order of the knobs (2 before 1, and 4 at the
bottom) follows no obvious logic and must be mapped for each model.

## Method

`research/map_test.py` binds IDs 1–24 to type their own two-digit number; then press
everything physically in a text field and read the order. `research/media_test.py` and
`media_test2.py` test hypotheses for the media format.
