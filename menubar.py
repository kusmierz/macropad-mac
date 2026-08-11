#!/usr/bin/env python3
"""
Makropad — menylinje-app.

Kjører daemonen inne i seg selv (event-tapen henger på NSApplication sin run-loop),
og serverer konfigurasjonsgrensesnittet lokalt.

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
    """En buntet app har ingen terminal å skrive til — uten dette er den
    umulig å feilsøke."""
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
    """Stien til .app-pakka når vi er frosset, ellers til python-skriptet."""
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
        self.prof_items = {}                 # navn -> MenuItem, for avkryssing
        prof_menu = rumps.MenuItem("Profil")
        for name in store.NAMES:
            it = rumps.MenuItem(name, callback=self.switch_profile)
            self.prof_items[name] = it
            prof_menu.add(it)
        self.menu = [
            rumps.MenuItem("Åpne konfigurasjon…", callback=self.open_config, key="k"),
            None,
            prof_menu,
            rumps.MenuItem("Aktiv", callback=self.toggle_active),
            rumps.MenuItem("Klargjør padden…", callback=self.prepare),
            None,
            rumps.MenuItem("Start ved innlogging", callback=self.toggle_login),
            None,
            rumps.MenuItem("Padde: sjekker…", callback=None),
            None,
            rumps.MenuItem("Avslutt Makropad", callback=self.quit, key="q"),
        ]
        self.start_server()
        self.start_daemon()
        self.menu["Start ved innlogging"].state = os.path.exists(AGENT)
        self.sync_profile_menu()

    # ── oppstart ────────────────────────────────────────────────────────
    def start_server(self):
        socketserver.TCPServer.allow_reuse_address = True
        try:
            self.server = socketserver.TCPServer(("127.0.0.1", PORT), config_app.Handler)
        except OSError:
            self.server = None      # noe annet bruker porten; konfig åpnes uansett
            return
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def start_daemon(self):
        """Prøv å ta tapen. Blokkerer aldri — en modal her ville fryst
        hovedtråden, og da hadde retry-timeren under aldri fått kjøre."""
        log(f"tilgang: {access.status()}")
        self.daemon = dmn.Daemon()
        ok = has_access() and dmn.install_tap(self.daemon)
        self.menu["Aktiv"].state = ok
        log(f"install_tap: {ok}")
        if ok:
            return
        self.menu["Padde: sjekker…"].title = "Trenger tilgang"
        request_access()          # macOS viser dialogen og legger appen i lista
        self.retry = rumps.Timer(self.retry_daemon, 2)
        self.retry.start()

    def retry_daemon(self, timer):
        """Poller til tilgangen er på plass. macOS gir den ikke til en prosess
        som allerede kjører, så vi starter oss selv på nytt."""
        if not has_access():
            return
        timer.stop()
        log("tilgang gitt — starter på nytt")
        target = app_path()
        if target.endswith(".app"):
            subprocess.Popen(["open", "-n", target])
        else:
            subprocess.Popen([sys.executable, target])
        rumps.quit_application()

    # ── meny ────────────────────────────────────────────────────────────
    def open_config(self, _):
        webbrowser.open(URL)

    def switch_profile(self, sender):
        """Bytt aktiv profil. Skriver fila og tvinger daemonen til å laste den."""
        store.set_active(sender.title)
        if self.daemon:
            self.daemon.load()               # reflekter umiddelbart
        self.sync_profile_menu()

    def sync_profile_menu(self):
        """Kryss av den aktive profilen. Leser disk så UI-endringer fanges opp òg."""
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
            rumps.alert("Velg enhetsmodell", "Åpne konfiguratoren og velg padden før klargjøring.")
            return
        model = device.get(model_id)
        count = len(model.targets())
        w = rumps.Window(
            title="Klargjør padden",
            message=(f"Skriver {count} signaler til {model.name}. Dette overskriver det som "
                     "ligger der fra før, og trengs bare én gang.\n\nEtterpå styrer du "
                     "alt fra konfigurasjonen — padden trenger aldri røres igjen."),
            ok="Skriv", cancel="Avbryt", dimensions=(0, 0))
        if not w.run().clicked:
            return
        try:
            n = config_app.flash_signals()
            rumps.notification("Makropad", "Padden er klar",
                               f"{n} signaler skrevet.")
        except Exception as e:
            rumps.alert("Kunne ikke skrive til padden",
                        f"{e}\n\nEr den koblet til?")

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
            label = device.get(model_id).board_id if model_id else "velg modell"
            self.menu["Padde: sjekker…"].title = f"Padde: tilkoblet · {label}"
        else:
            self.menu["Padde: sjekker…"].title = "Padde: frakoblet"
        if dmn.TAP and not dmn.is_enabled() and self.menu["Aktiv"].state:
            dmn.set_enabled(True)      # macOS slår av tapen ved treghet
        self.sync_profile_menu()       # fang opp profilbytte gjort i UI-et


if __name__ == "__main__":
    # Alt daemonen skriver havner i loggen — ellers er en buntet app stum.
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        sys.stdout = sys.stderr = open(LOG, "a", buffering=1)
    except Exception:
        pass
    log("── start ──────────────────────────────")
    NSApplication.sharedApplication().setActivationPolicy_(
        NSApplicationActivationPolicyAccessory)   # ingen Dock-ikon
    try:
        MakropadApp().run()
    except Exception:
        import traceback
        log("KRASJ:\n" + traceback.format_exc())
        raise
