#!/usr/bin/env python3
"""
Makropad — grafisk konfigurator.

Redigerer profiles.yaml: hva hver tast og knott gjør, per app. Daemonen plukker opp
endringene med det samme du lagrer.

    .venv/bin/python app.py        # åpner http://127.0.0.1:8777
"""
import http.server
import json
import os
import socketserver
import subprocess
import threading
import webbrowser

import actions
import daemon as dmn
import device
import keys
import paths
import signals
import store
import xzkj

PORT = 8777
PROFILES = paths.PROFILES
EXAMPLE = paths.EXAMPLE


def running_apps():
    """Apper med vindu — til app-velgeren."""
    try:
        from AppKit import NSWorkspace
        out = []
        for a in NSWorkspace.sharedWorkspace().runningApplications():
            if a.activationPolicy() == 0 and a.bundleIdentifier():
                out.append({"name": a.localizedName(), "bundle": a.bundleIdentifier()})
        return sorted(out, key=lambda x: x["name"].lower())
    except Exception:
        return []


def flash_signals(model_id=None):
    model_id = model_id or store.active_model(store.load())
    if model_id is None:
        raise ValueError("Velg enhetsmodell før padden klargjøres")
    plan = []
    for t in signals.targets(model_id):
        parts = signals.spec_for(t, model_id).split("+")
        entries = [(0, xzkj.MODIFIERS[m]) for m in parts[:-1]]
        entries.append((0, xzkj.HID_CODES[parts[-1]]))
        plan.append((device.resolve(t, model_id), entries))
    h = xzkj.open_vendor_interface()
    try:
        for kid, entries in plan:
            xzkj.bind_key_sequence(h, kid, entries, layer=1)
        xzkj.finish(h)
    finally:
        h.close()
    return len(plan)


def daemon_running():
    try:
        out = subprocess.run(["pgrep", "-f", "daemon.py"], capture_output=True, text=True)
        return bool(out.stdout.strip())
    except Exception:
        return False


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(paths.resource("ui.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/state":
            doc = store.load()
            model_id = store.active_model(doc)
            self._json({
                "doc": doc,
                "activeModel": model_id,
                "models": device.public_models(),
                "profileNames": store.NAMES,
                "targets": signals.targets(model_id) if model_id else [],
                "media": sorted(actions.NX),
                "keys": sorted(keys.VK),
                "categories": [{"id": i, "en": en, "no": no, "keys": ks}
                               for i, en, no, ks in keys.CATEGORIES],
                "symbols": keys.SYMBOL,
                "mods": list(keys.MODS),
                "saved": os.path.exists(PROFILES),
            })
        elif self.path == "/api/capture/poll":
            r = dmn.capture_result()
            self._json({"done": bool(r), "spec": r})
        elif self.path == "/api/lastpress":
            self._json(dmn.last_press())
        elif self.path == "/api/status":
            try:
                h = xzkj.open_vendor_interface(); h.close()
                connected = True
            except Exception:
                connected = False
            self._json({"connected": connected, "daemon": daemon_running()})
        elif self.path == "/api/apps":
            self._json({"apps": running_apps()})
        else:
            self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n) or "{}")
        if self.path == "/api/save":
            try:
                model_id = data.get("active_model")
                if model_id is not None and model_id not in device.MODELS:
                    raise ValueError(f"Ukjent enhetsmodell: {model_id!r}")
                self._json({"ok": True, "doc": store.save(data)})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        elif self.path == "/api/model":
            try:
                self._json({"ok": True, "doc": store.set_model(data.get("model"))})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        elif self.path == "/api/validate":
            try:
                actions.validate(data.get("action", ""))
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        elif self.path == "/api/flash":
            try:
                self._json({"ok": True, "count": flash_signals(data.get("model"))})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        elif self.path == "/api/test":
            try:
                actions.run(data.get("action", ""))
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        elif self.path == "/api/capture/start":
            if not dmn.TAP:
                self._json({"ok": False, "error": "tap"})
            else:
                dmn.capture_start()
                self._json({"ok": True})
        elif self.path == "/api/capture/cancel":
            dmn.capture_stop()
            self._json({"ok": True})
        else:
            self.send_error(404)


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://127.0.0.1:{PORT}"
        print(f"Makropad-konfigurator kjører på {url}  (Ctrl+C for å avslutte)")
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nAvsluttet.")
