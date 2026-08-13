# Protocol — XZKJ macropads (`514C:8850`)

This document is the consolidated protocol record for the XZKJ macropads supported by this
repository. Findings were collected on macOS from a physical 4×4/3-knob unit, from offline
inspection of the vendor application, and from the upstream sources listed below.

`514C:8850` is reused by at least `@XZKJ-16key_3knob` and `@XZKJ-12key_4knob`. The VID/PID
therefore identifies a protocol family, not the physical layout. Software must require an
explicit model selection before it writes key bindings.

## Final decisions

- Use the vendor HID interface on usage page `0xFF00`, interface 0.
- Send 65-byte output reports, including report ID `0x03` and trailing zero padding.
- Encode LED state as a mode followed immediately by exactly 16 RGB triplets. There is no
  separate base-color triplet on the tested firmware.
- Do not copy the extra `base_color` field from upstream PR #175. Its code duplicates the
  first palette entry and shifts the remaining entries by one physical LED.
- Treat LED layers as 0-based (`0`–`2`) and key-binding layers as 1-based (`1`–`3`).
- Prefer LED modes 0 and 1 in production. Modes 2–5 are useful but cannot be considered
  reliable because the device's LED engine can lock without further USB traffic.
- Configure the desired LED state whenever the device attaches. A physical reconnect is the
  only verified recovery from an LED-engine lock.
- Retain only the findings from offline vendor-software inspection; no downloaded vendor
  artifact is kept or executed.

## Transport

The device exposes a vendor HID interface for configuration and standard keyboard, mouse,
and consumer-control interfaces for input. On the tested macOS installation, opening the
vendor interface requires `sudo`.

```python
devs = [
    d for d in hid.enumerate(0x514C, 0x8850)
    if d["usage_page"] == 0xFF00 and d.get("interface_number") == 0
]
h = hid.device()
h.open_path(devs[0]["path"])
```

All output frames shown below are padded with zeroes to 65 bytes for the macOS hidapi path,
including report ID `0x03`. PR #175 accumulates 64-byte messages including the same report
ID; this is a host transport/framing difference, not evidence for a different command
prefix.

## LEDs

### Write state

Write one mode and one 48-byte palette to a layer:

```text
offset  0     1     2     3      4     5 ... 52
        0x03  0xFE  0xB0  layer  mode  (red, green, blue) × 16
```

- `layer`: `0`–`2`.
- `mode`: `0`–`5`.
- Palette: exactly 48 bytes in ordinary RGB order.
- Repeating `FF 00 00` 16 times displays solid red in static mode.

The vendor application's default 48-byte palette is:

```text
ff0000 ff8030 ffff30 00ff00 00ffff 0000ff 800080 8b0000
ffa500 ffff96 7dff00 008b8b 00008b ff00ff ff6666 ffc864
```

### Read saved state

Request one layer:

```text
03 FA B0 <layer>
```

The logical response body contains one mode byte followed by the 48-byte palette. With the
macOS hidapi path used here, the 64-byte read retains a leading `03 FA` pair, so the mode is
at offset 2 and the palette occupies offsets 3–50.

Readback reports persistent device storage, not necessarily the current visible output. A
write can be stored and read back successfully while a locked LED engine ignores it. After
reconnection, the device loads the last stored state.

### Verified modes

| Mode | Name used here | Observed behavior on the tested 4×4 unit | Status |
|---|---|---|---|
| `0` | `off` | All LEDs off. | Suitable for production. |
| `1` | `static` | Displays the supplied 16-color palette continuously. | Suitable for production once visibly active. |
| `2` | `reactive` | Dark while idle; only the held key lights and turns off on release. | Firmware lock risk. |
| `3` | `ripple` | Dark while idle; a held key lights its complete row and column in multiple colors. | Firmware lock risk. |
| `4` | `rainbow-rows` | Sequential color propagation/pulse, then a settled rainbow-like palette. | Firmware lock risk. |
| `5` | `rainbow-cols` | Several left-to-right pulses, then stops. | Firmware lock risk. |

The names follow the exact-device implementation in upstream PR #175. The descriptions are
local hardware observations and are more precise than the names. The PR parser also accepts
`rainbow` as an alias for `rainbow-rows`.

### Firmware limitation

The LED engine can stop reacting after an unpredictable interval, including while mode 2 is
active and no new script or USB write is running. Once locked:

- reactive effects may stop;
- later writes may read back correctly without changing visible LEDs;
- reconnecting the USB device restores rendering and applies the last stored state.

The same fault was independently reproduced on the same `@XZKJ-16key_3knob` model in
[upstream PR #175](https://github.com/kriomant/ch57x-keyboard-tool/pull/175), with measured
times from 2 seconds to 2 minutes 18 seconds. No host-side reset or unlock command has been
verified.

PR #175 places an additional three-byte base color before the 16 per-key colors. Its code
sets that base color to the first configured color, then emits the same first color again as
palette slot 0. On the tested firmware, bytes 5–7 already represent physical LED 1, so this
duplicates the first color, shifts PR slots 0–14 onto physical LEDs 2–16, and leaves PR slot
15 outside the consumed 48-byte palette. This exactly explains the independent PR comment
that slot 0 lit the first two keys and slot 15 had no visible effect.

The format documented here—48 palette bytes immediately after the mode—matches vendor
object code, device readback, and direct hardware palette tests. The PR's extra field is
recorded as an upstream implementation discrepancy, not part of this protocol.

## Key bindings (type `0x01`)

```text
offset  0     1     2       3      4     5     6      7 ...
        0x03  0xFD  key_id  layer  0x01  0x00  count  (delay_hi, delay_lo, hid_code) × count
```

- `layer` is 1-based (`1`–`3`).
- `count` is at most 18; modifiers count toward the limit.
- Each entry is a 16-bit big-endian delay in milliseconds followed by a HID usage ID.

Modifiers are separate sequence entries and apply to the first non-modifier that follows:

| Code | Modifier | Code | Modifier |
|---|---|---|---|
| `0xF1` | Left Ctrl | `0xF5` | Right Ctrl |
| `0xF2` | Left Shift | `0xF6` | Right Shift |
| `0xF3` | Left Alt | `0xF7` | Right Alt |
| `0xF4` | Left Meta/Cmd | `0xF8` | Right Meta |

Example: `Ctrl+Alt+Delete` on key ID 1, layer 1:

```text
03 FD 01 01 01 00 03  00 00 F1  00 00 F3  00 00 4C
```

PR #175 bundles an earlier K8850 binding commit which uses a different macro encoding: two
zero bytes after `count`, followed by `(hid_code, 0x00, 0x32)` entries. That encoding is not
used here. The current merged upstream `k8850_4x4.rs`, the local implementation, and local
tests all use the format documented above: `(0x00, 0x00, hid_code)` for a zero-delay entry.
The PR's bundled key-binding commit should be treated as superseded and must not be mixed
with the LED findings.

## Mouse clicks (type `0x03`)

The locally verified 12-key/4-knob click frame is:

```text
03 FD key_id layer 03 00 01 00 buttons
```

`buttons` is a bitmask: `1` = left, `2` = right, `4` = middle.

PR #175 uses the following 16-key/3-knob mouse payload after the common
`03 FD key_id layer 03` prefix:

```text
01 04 00 00 modifier 00 00 buttons 00 00 dx 00 00 dy 00 00 wheel
```

Its code supports click, signed movement, wheel, and a best-effort drag. The author warns
that drag may not work correctly because the firmware may treat button hold and movement as
separate actions. The current merged upstream driver rejects drag instead of attempting it.

## Media

On this device, volume and mute are keyboard-page codes written with binding type `0x01`:

| Code | Function |
|---|---|
| `0x7F` | Mute |
| `0x80` | Volume up |
| `0x81` | Volume down |

The current merged exact 16-key/3-knob driver uses consumer type `0x02`:

```text
03 FD key_id layer 02 00 02 00 00 consumer_code_low 00 00 consumer_code_high
```

PR #175's bundled key-binding commit emits only the low byte and includes a byte-generation
test with play/pause `0xCD`; the PR author also reports hardware testing of media bindings.
Local tests of consumer encodings did not produce a response on the other tested
`514C:8850` variant. Therefore the full frame above is the upstream implementation for
`@XZKJ-16key_3knob`, but play/pause, next, and previous remain unverified for every layout
and firmware sharing the VID/PID.

## Finalizing key programming

Both PR #175 and the current merged exact-device driver send this packet immediately after
every key binding:

```text
03 FD FE FF
```

This repository currently wraps it in a sequence retained from the related k884x
implementation:

```text
03 AA AA
03 FD FE FF
03 AA AA
```

The surrounding `03 AA AA` packets in `xzkj.finish()` have not been independently verified
on PID `8850`. Only the central per-binding finalize packet has exact-device upstream
support.

## Key ID maps

### `@XZKJ-16key_3knob`

The 4×4/3-knob model is row-major: physical keys 1–16 map to key IDs 1–16. Knob actions use
IDs 17–25: knob 1 uses 17–19, knob 2 uses 20–22, and knob 3 uses 23–25, each ordered left,
press, right. This map comes from the exact-device upstream implementation and is consistent
with the unit used for the LED tests.

### `@XZKJ-12key_4knob`

This layout counts keys from bottom to top, column by column rather than in reading order.
The map was measured by binding each ID to type its own number.

Physical numbering used by the software and README:

```text
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

Knobs:

| Knob | Turn left | Press | Turn right |
|---|---|---|---|
| 1 (small, upper left) | 19 | 20 | 21 |
| 2 (small, lower left) | 16 | 17 | 18 |
| 3 (medium) | 22 | 23 | 24 |
| 4 (large) | 13 | 14 | 15 |

Knob 4 reuses the range that represents an additional key row on related layouts. The knob
ordering is model-specific and must not be inferred from VID/PID.

## Evidence and sources

### Local files

| Path | Purpose/status |
|---|---|
| `xzkj.py` | Production frame construction: `write_leds()` and `write_led_color()`. |
| `research/map_test.py` | Empirical key/knob ID mapper. |
| `research/probe.py` | Vendor-interface discovery and access check. |
| `tests/test_baseline_contract.py` | Unit contract for complete frames, validation, layers, and uniform color writes. |

### Vendor software evidence

The software came from the vendor's
[mini-keyboard support page](https://sikaicase.com/blogs/support/setting-for-software).
Offline inspection established that the vendor write routine constructs
`03 FE B0 layer mode` and copies exactly 48 palette bytes, while the read routine uses
`03 FA B0 layer`. The inspected data also contained three copies of the default palette.
The vendor program was never executed, and no extracted artifacts are retained.

### PR #175 code audit

[PR #175](https://github.com/kriomant/ch57x-keyboard-tool/pull/175) was still open on
2026-08-13 and consists of two commits: exact-device key binding support (`1ec60b7`) and LED
support (`a2700fc`). The LED implementation in its second commit has these concrete
behaviors:

- It defines modes 0–5 as `off`, `static`, `reactive`, `ripple`, `rainbow-rows`, and
  `rainbow-cols`; `rainbow` aliases mode 4.
- Its CLI syntax is `led <layer 0-2> <mode>`; `static`, `reactive`, and `ripple` require a
  color argument, while `off` and the rainbow modes do not.
- It accepts case-insensitive named colors `red`, `green`, `blue`, `white`, `yellow`,
  `cyan`, `magenta`, `orange`, and `purple`, plus `#RRGGBB`.
- It constructs `03 FE B0 layer mode base_R base_G base_B`, then appends 16 RGB entries.
  For YAML, `base_color` is the first flattened palette color. For the CLI, one color is
  repeated as both the base and all 16 entries.
- It flattens the YAML color matrix without checking its dimensions. Missing entries become
  black, entries after the first 16 are ignored, and an empty matrix makes the base black.
- The single-layer CLI command always emits three reports: the selected layer receives the
  requested mode and uniform color, while the other two layers are explicitly set to off.
- A YAML upload emits no LED reports when every layer omits `leds`. If any layer contains
  `leds`, the driver emits all three reports and explicitly turns off every layer without a
  configuration. This contradicts the PR description's claim that omitted layers are left
  unchanged; the code is authoritative for actual behavior.
- Shared configuration code carries the optional per-layer `leds` value opaquely; parsing
  its `mode` and `colors` fields remains specific to the K8850 driver.
- It generates reports only. It implements no LED readback, freeze detection, retry, reset,
  or recovery command.
- Its driver accepts at most 16 buttons and 3 knobs, so it does not cover the
  `@XZKJ-12key_4knob` layout despite the shared VID/PID.

The PR's unit tests validate parsing and generated bytes, including static red and mode off.
The PR author separately reports hardware testing of all modes, per-layer YAML colors,
combined key/LED uploads, and the freeze. A second hardware tester confirmed the shifted
slot behavior and that reconnecting is required after a lock.

### Upstream references

- [`ch57x-keyboard-tool` issue #153](https://github.com/kriomant/ch57x-keyboard-tool/issues/153):
  exact VID/PID and `@XZKJ-16key_3knob`; source of the 65-byte `03 FD` key-binding protocol.
- [`ch57x-keyboard-tool` PR #175](https://github.com/kriomant/ch57x-keyboard-tool/pull/175):
  open exact-device implementation and hardware discussion analyzed above.
- [`k8850_4x4.rs`](https://github.com/kriomant/ch57x-keyboard-tool/blob/master/src/keyboard/k8850_4x4.rs):
  current merged exact-device key, knob, media, and mouse implementation; it agrees with
  this repository's key-entry ordering and does not contain LED support.
- [`k884x.rs`](https://github.com/kriomant/ch57x-keyboard-tool/blob/master/src/keyboard/k884x.rs):
  related older family with similar named LED modes but a different packet layout.
- [`ch57x-keyboard-tool` issue #180](https://github.com/kriomant/ch57x-keyboard-tool/issues/180):
  evidence that k884x LED layouts are model-specific and cannot safely be transferred to a
  different PID or physical layout.

## Reproducible commands

Hardware discovery:

```sh
sudo .venv/bin/python research/probe.py
```

Repository validation:

```sh
.venv/bin/python -m py_compile xzkj.py
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

## Validation status

- Hardware: vendor HID discovery and opening passed under `sudo`.
- Hardware: LED writes and readback passed for all three layers.
- Hardware: modes 0–5 were observed after reconnecting when necessary; modes 2 and 3 were
  also exercised by pressing keys.
- Hardware: the ordinary RGB format was confirmed with uniform red and repeating red,
  green, blue, white palettes.
- Hardware: persistence across reconnect and the independent visible-engine lock were
  confirmed.
- Automated: all 23 discovered unit tests pass, including the LED frame/validation contract
  in `tests/test_baseline_contract.py`.
- Static: `py_compile xzkj.py` and `git diff --check` pass.

## Accepted limitations

- macOS HID access currently requires `sudo`; no permission/entitlement solution is part of
  this protocol work.
- Modes 2–5 are documented but not promised as reliable application features.
- The device stores LED changes independently of whether its visible LED engine applies them.
- Recovery instructions may require a physical USB reconnect.
- The vendor Windows program was treated as untrusted reference material and never executed.
- PR #175 is a useful independent implementation, not the source of truth where its packet
  layout conflicts with vendor code, readback, and direct hardware tests.

## Unresolved risks

- One-hot LED-slot-to-physical-key mapping has not been completed across both layouts that
  reuse `514C:8850`. The byte format is verified; universal physical slot ordering is not.
- VID/PID-only model detection could program the wrong key or knob because multiple layouts
  share the identifier.
- No software reset/unlock command for the LED engine is known.
- Consumer-control media is reported working by PR #175 on `@XZKJ-16key_3knob` but remains
  unverified on other layouts and firmware revisions using the same VID/PID.
- The two surrounding `03 AA AA` packets in `xzkj.finish()` remain unverified on PID `8850`;
  PR #175 supports sending `03 FD FE FF` after each binding.
- Firmware revisions may differ from the tested unit; the readback and a diagnostic palette
  should be checked before assuming identical LED behavior on another device.
