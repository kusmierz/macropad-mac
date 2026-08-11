#!/usr/bin/env python3
"""
Makropad — menu-bar app.

Runs the daemon internally (the event tap attaches to NSApplication's run loop)
and serves the configuration interface locally.

    .venv/bin/python menubar.py
"""
import os
import socketserver
import subprocess
import sys
import threading
import webbrowser

import rumps
import Quartz
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

import access
import app as config_app
import daemon as dmn
import device
import paths
import store
import xzkj

PORT = 8777
URL = f"http://127.0.0.1:{PORT}"
AGENT_DIR = os.path.expanduser("~/Library/LaunchAgents")
AGENT = os.path.join(AGENT_DIR, "no.macropad.menubar.plist")
LOG = os.path.expanduser("~/Library/Logs/Makropad.log")


def log(msg):
    """A bundled app has no terminal to write to — this makes it debuggable."""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(f"{__import__('datetime').datetime.now():%H:%M:%S}  {msg}\n")
    except Exception:
        pass

ICON_ON = "MenubarIconTemplate.png"
resource = paths.resource


SETTINGS_AX = ("x-apple.systempreferences:com.apple.preference.security"
               "?Privacy_Accessibility")


has_access = access.have_all
request_access = access.request_all


def app_path():
    """The .app bundle path when frozen, otherwise the Python script path."""
    if getattr(sys, "frozen", False):
        # …/Makropad.app/Contents/MacOS/Makropad
        return os.path.abspath(os.path.join(os.path.dirname(sys.executable),
                                            "..", "..", ".."))
    return os.path.abspath(__file__)


class MakropadApp(rumps.App):
    def __init__(self):
        super().__init__("Makropad", icon=resource(ICON_ON), template=True, quit_button=None)
        self.server = None
        self.daemon = None
        self.prof_items = {}                 # name -> MenuItem, used for checkmarks
        prof_menu = rumps.MenuItem("Profile")
        for name in store.NAMES:
            it = rumps.MenuItem(name, callback=self.switch_profile)
            self.prof_items[name] = it
            prof_menu.add(it)
        self.menu = [
            rumps.MenuItem("Open configuration…", callback=self.open_config, key="k"),
            None,
            prof_menu,
            rumps.MenuItem("Active", callback=self.toggle_active),
            rumps.MenuItem("Prepare pad…", callback=self.prepare),
            None,
            rumps.MenuItem("Launch at login", callback=self.toggle_login),
            None,
            rumps.MenuItem("Pad: checking…", callback=None),
            None,
            rumps.MenuItem("Quit Makropad", callback=self.quit, key="q"),
        ]
        self.start_server()
        self.start_daemon()
        self.menu["Launch at login"].state = os.path.exists(AGENT)
        self.sync_profile_menu()

    # ── oppstart ────────────────────────────────────────────────────────
    def start_server(self):
        socketserver.TCPServer.allow_reuse_address = True
        try:
            self.server = socketserver.TCPServer(("127.0.0.1", PORT), config_app.Handler)
        except OSError:
            self.server = None      # another process uses the port; configuration still opens
            return
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def start_daemon(self):
        """Try to install the tap. Never block — a modal would freeze the main
        thread and prevent the retry timer below from running."""
        log(f"access: {access.status()}")
        self.daemon = dmn.Daemon()
        ok = has_access() and dmn.install_tap(self.daemon)
        self.menu["Active"].state = ok
        log(f"install_tap: {ok}")
        if ok:
            return
        self.menu["Pad: checking…"].title = "Permission required"
        request_access()          # macOS displays its dialog and adds the app to the list
        self.retry = rumps.Timer(self.retry_daemon, 2)
        self.retry.start()

    def retry_daemon(self, timer):
        """Poll until permission is granted. macOS does not grant it to an
        already-running process, so restart the application."""
        if not has_access():
            return
        timer.stop()
        log("permission granted — restarting")
        target = app_path()
        if target.endswith(".app"):
            subprocess.Popen(["open", "-n", target])
        else:
            subprocess.Popen([sys.executable, target])
        rumps.quit_application()

    # ── menu ────────────────────────────────────────────────────────────
    def open_config(self, _):
        webbrowser.open(URL)

    def switch_profile(self, sender):
        """Change the active profile, write it, and force a daemon reload."""
        store.set_active(sender.title)
        if self.daemon:
            self.daemon.load()               # reflect immediately
        self.sync_profile_menu()

    def sync_profile_menu(self):
        """Check the active profile. Read disk so UI changes are also picked up."""
        try:
            doc = store.load()
            model_id = store.active_model(doc)
            active = store.model_doc(doc, model_id)["active"] if model_id else None
        except Exception:
            return
        for name, item in self.prof_items.items():
            item.state = (name == active)

    def toggle_active(self, sender):
        if not dmn.TAP:
            self.ask_access()
            return
        sender.state = not sender.state
        dmn.set_enabled(sender.state)

    def prepare(self, _):
        model_id = store.active_model(store.load())
        if not model_id:
            rumps.alert("Select a device model",
                        "Open the configurator and select the pad before preparing it.")
            return
        model = device.get(model_id)
        count = len(model.targets())
        w = rumps.Window(
            title="Prepare pad",
            message=(f"Writes {count} signals to {model.name}. This overwrites existing "
                     "bindings and is needed only once.\n\nAfterward, configuration "
                     "controls everything — you never need to touch the pad again."),
            ok="Write", cancel="Cancel", dimensions=(0, 0))
        if not w.run().clicked:
            return
        try:
            n = config_app.flash_signals()
            rumps.notification("Makropad", "Pad is ready",
                               f"{n} signals written.")
        except Exception as e:
            rumps.alert("Could not write to the pad",
                        f"{e}\n\nIs it connected?")

    def toggle_login(self, sender):
        if sender.state:
            subprocess.run(["launchctl", "unload", AGENT], capture_output=True)
            if os.path.exists(AGENT):
                os.remove(AGENT)
            sender.state = False
            return
        target = app_path()
        prog = (f"<string>open</string><string>-a</string><string>{target}</string>"
                if target.endswith(".app")
                else f"<string>{sys.executable}</string><string>{target}</string>")
        os.makedirs(AGENT_DIR, exist_ok=True)
        with open(AGENT, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                    '<plist version="1.0"><dict>\n'
                    '  <key>Label</key><string>no.macropad.menubar</string>\n'
                    f'  <key>ProgramArguments</key><array>{prog}</array>\n'
                    '  <key>RunAtLoad</key><true/>\n'
                    '</dict></plist>\n')
        subprocess.run(["launchctl", "load", AGENT], capture_output=True)
        sender.state = True

    def quit(self, _):
        if self.server:
            self.server.shutdown()
        rumps.quit_application()

    # ── status ──────────────────────────────────────────────────────────
    @rumps.timer(5)
    def poll(self, _):
        try:
            h = xzkj.open_vendor_interface(); h.close()
            ok = True
        except Exception:
            ok = False
        if ok:
            model_id = store.active_model(store.load())
            label = device.get(model_id).board_id if model_id else "select model"
            self.menu["Pad: checking…"].title = f"Pad: connected · {label}"
        else:
            self.menu["Pad: checking…"].title = "Pad: disconnected"
        if dmn.TAP and not dmn.is_enabled() and self.menu["Active"].state:
            dmn.set_enabled(True)      # macOS disables the tap when it is slow
        self.sync_profile_menu()       # pick up profile changes made in the UI


if __name__ == "__main__":
    # Everything written by the daemon goes to the log; otherwise a bundled app is silent.
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        sys.stdout = sys.stderr = open(LOG, "a", buffering=1)
    except Exception:
        pass
    log("── start ──────────────────────────────")
    NSApplication.sharedApplication().setActivationPolicy_(
        NSApplicationActivationPolicyAccessory)   # no Dock icon
    try:
        MakropadApp().run()
    except Exception:
        import traceback
        log("CRASH:\n" + traceback.format_exc())
        raise
