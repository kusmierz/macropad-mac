# The Daemon — app-dependent keys

The pad alone can only send fixed keystrokes. The daemon turns it into something that knows
which app you are using: the same knob can seek in Spotify and zoom in Figma.

It also handles media transport. The pad has no working consumer codes for
play/pause/next/previous (see [PROTOCOL.md](PROTOCOL.md)) — but it does not need them,
because the daemon sends those commands through macOS's own APIs instead.

## How it works

```
   Pad                 Daemon                      macOS
   ───                 ──────                      ─────
   knob 3 right   →  cmd+ctrl+shift+alt+F17  →  looks up profiles.yaml
                                                ├─ Spotify in front?  → media:next
                                                └─ otherwise          → media:next
                                             →  sends NX_KEYTYPE_NEXT, swallows the signal
```

The pad is flashed **once** with 24 unique signals. After that, you only change
`profiles.yaml` — the pad never needs to be touched again.

### Why F13–F20?

They do not exist on Mac keyboards, so nothing else uses them. macOS defines
virtual key codes only for F13–F20 (eight), so we use three modifier levels to
get 24 unique signals: unmodified, `ctrl+shift+alt+`, and `cmd+ctrl+shift+alt+`.
See `signals.py` for the map.

## Setup

```bash
.venv/bin/python setup_daemon.py --dry    # preview the plan
.venv/bin/python setup_daemon.py          # flash the signals (once)
cp profiles.example.yaml profiles.yaml    # your configuration
.venv/bin/python daemon.py
```

**Accessibility permission is required.** The daemon uses a `CGEventTap`, and macOS requires
permission: System Settings → Privacy & Security → Accessibility → add the application
you use to start the daemon (Terminal, iTerm, VS Code …). Without this,
`CGEventTapCreate` returns null and the daemon reports the problem.

## `profiles.yaml`

```yaml
default:
  knob3.press: media:playpause
  key5:        key:cmd+c

apps:
  com.spotify.client:          # substring of bundle ID, case-insensitive
    knob3.left:  media:prev
```

Anything not overridden for the app in front falls back to `default`.
The file is reloaded automatically when you save it.

### Actions

| Syntax | Action |
|---|---|
| `media:playpause` `media:next` `media:prev` | media transport |
| `media:mute` `media:volumeup` `media:volumedown` | volume |
| `key:cmd+shift+4` | send a key combination |
| `app:Spotify` | activate or launch an app |
| `url:https://…` | open a URL |
| `shell:…` | run a command |
| `none` | swallow the signal |

Find an app's bundle ID:

```bash
osascript -e 'id of app "Spotify"'
```

## Start automatically at login

```bash
cp launchd/no.macropad.daemon.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/no.macropad.daemon.plist
```

Log: `/tmp/macropad-daemon.log`. Stop with `launchctl unload …`.

## Troubleshooting

**“Could not create event tap”** — Accessibility permission is missing; see above. If you
granted permission before, it may be tied to an old binary path; remove and add it again.

**Nothing happens when you press** — run `setup_daemon.py` again and check that
the pad is actually sending: bind a key to something visible with `app.py` and test in a text field.

**Signals leak into other apps** — the daemon swallows only signals it recognizes.
If it is not running, F13–F20 go straight to the app in front (usually harmless).
