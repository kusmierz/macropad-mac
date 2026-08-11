# macropad-mac

macOS configurator for the AliExpress **XZKJ 12-key / 4-knob** and **16-key / 3-knob** macropads
(USB `514C:8850`). The same USB ID is used by both, so the ID alone does not identify the layout.

The protocol was reverse-engineered from scratch for this variant. The configuration is stored
in the keyboard's own memory, so the software is only needed when you change the layout.

## Is this your device?

<img src="design/device.png" width="560" alt="XZKJ 12-key/4-knob macropad">

Supported models are `@XZKJ-12key_4knob` (twelve keys in a 4×3 layout and four knobs) and
`@XZKJ-16key_3knob` (sixteen keys in a 4×4 layout and three knobs). Choose the model explicitly
in the configurator before preparing the pad.

```bash
hidutil list | grep 514c
```

The vendor's [support page for the mini-keyboard software](https://sikaicase.com/blogs/support/setting-for-software)
lists Windows software and a separate macOS download. The macOS software does not work as
expected with this device, so this project provides the working macOS configurator instead.

## Getting started

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py          # opens http://127.0.0.1:8777
```

<img src="design/taktil_stillhet_makropad.png" width="720" alt="Interface">

1. Choose the model, then **prepare the pad** — once. This writes 24 or 25 invisible signals.
2. Click a key or knob in the diagram and choose what it should do.
3. Start the daemon: `.venv/bin/python daemon.py`

The pad never needs to be reflashed again. Everything you change in the interface takes effect
immediately — the daemon reloads the profile whenever it is saved.

Profiles are stored separately per model. Daemon signal mode supports USB and the included
receiver; native Bluetooth does not reliably emit the extended F-key signals it requires.

The daemon requires **Accessibility permission**: System Settings → Privacy & Security →
Accessibility → add the application you use to start it.

## What a key can do

| Type | Example | |
|---|---|---|
| `media` | `playpause` `next` `prev` `mute` `volumeup` | use native macOS media keys |
| `key` | `cmd+c` `cmd+shift+4` | send a keyboard shortcut |
| `app` | `Spotify` | activate or launch an app |
| `url` | `https://…` | open a link |
| `shell` | `say done` | run a command |

Each knob provides three independent actions: **turn left · press · turn right**.

### Profiles

Three profiles — **Profile 1 / 2 / 3** — each with its own complete layout (default settings +
app overrides). Change the active profile at the top of the interface or from the menu bar
(the **Profile** menu). The daemon dispatches actions from the active profile; switching takes
effect immediately.

The profiles live in software, not on the pad. This is intentional: on this device, the host
cannot determine which physical layer the pad is using (the firmware sends no notification),
and the signal model cannot accommodate three layers of unique, collision-free signals.
Software profiles provide the same result without that uncertainty.

### Per-app overrides

Add an app with **+** in the interface, then override only the keys you want to behave
differently in that app — the rest are inherited from the default profile (shown dimmed in the
diagram). The same knob can seek in Spotify and zoom in VS Code. App overrides are per profile.

```yaml
default:
  knob3.press: media:playpause
apps:
  com.spotify.client:
    knob3.left:  media:prev
    knob3.right: media:next
```

See [docs/DAEMON.md](docs/DAEMON.md) for details on how it works.

## Without the daemon

If you prefer fixed bindings stored on the pad — with no software running and no Accessibility
permission — use the CLI. You lose app-specific behavior and media transport controls, but
volume, keyboard, and mouse actions still work:

```bash
.venv/bin/python macroctl.py flash config.example.yaml
.venv/bin/python macroctl.py flash config.16key.example.yaml
.venv/bin/python macroctl.py list-keys
```

Syntax: `cmd+c`, `cmd+shift+4`, `h,e,i` (sequence), `c@100` (delay),
`volumeup`/`volumedown`/`mute`, `mouse:left`.

### Layout orientation

The YAML layout can describe the pad in the orientation in which you use it:

```yaml
orientation: vertical       # horizontal or vertical
knobs_location: top        # left/right when horizontal; top/bottom when vertical
```

Keys are then read from the `keys` matrix in that physical orientation. Knobs are numbered
left-to-right on a top/bottom edge and top-to-bottom on a left/right edge.

## Status

- ✅ Key bindings, modifiers, sequences, and delays
- ✅ Volume up/down/mute directly from the pad
- ✅ Mouse clicks
- ✅ App-specific keys and full media transport controls through the daemon
- ✅ Three software profiles (`Profile 1/2/3`), switchable from the UI or menu bar
- ⚠️ Play/pause/next/previous *directly from the pad* — consumer format not found
      (in practice, the daemon makes this unnecessary)
- ⬜ LED control
- ⬜ Physical hardware layers (the protocol has a `layer` byte, but the host cannot read the
      active layer — software profiles are used instead)

See [docs/PROTOCOL.md](docs/PROTOCOL.md) for the key ID map and protocol details.

## Acknowledgments

[kriomant/ch57x-keyboard-tool](https://github.com/kriomant/ch57x-keyboard-tool), especially
[@yawor's work in issue #153](https://github.com/kriomant/ch57x-keyboard-tool/issues/153),
which cracked the `03 fd` frame format on a related 16-key/3-knob variant. This project maps
the 12-key/4-knob variant and finds that its media keys use the keyboard usage page rather than
the consumer usage page.

## License

MIT
