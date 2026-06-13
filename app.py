from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote
import ctypes
import json
import mimetypes
import os
import signal
import socket
import threading
import time
import webbrowser
from datetime import datetime, timezone

from core import network
from core.hotkeys import HotkeyManager
from core.paths import app_dir, bundle_dir
from core.settings import load_settings, save_settings


HOST = "127.0.0.1"
PORT = 8787
MUTEX_NAME = "Local\\LaxyControl"
ERROR_ALREADY_EXISTS = 183
APP_DIR = app_dir()
BUNDLE_DIR = bundle_dir()
WEB_ROOT = BUNDLE_DIR / "web"
APP_NAME = "LaxyControl"
AUDIT_LOG = APP_DIR / "audit.log"
MUTEX_HANDLE = None


def acquire_single_instance():
    if os.name != "nt":
        return True

    global MUTEX_HANDLE
    kernel32 = ctypes.windll.kernel32
    MUTEX_HANDLE = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not MUTEX_HANDLE:
        return True

    return kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def wait_for_service(timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if service_is_running():
            return True
        time.sleep(0.1)
    return service_is_running()


def service_is_running():
    try:
        with socket.create_connection((HOST, PORT), timeout=0.3):
            return True
    except OSError:
        return False


class OverlayController:
    def __init__(self, app):
        self.app = app
        self.root = None
        self.label = None
        self.thread = None
        self.running = False
        self.visible = False

    def start(self):
        if self.running:
            return True

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True

    def _run(self):
        try:
            import tkinter as tk
        except Exception as exc:
            self.app.set_last_result(False, f"Overlay unavailable: {exc}")
            return

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_NAME)
        self.root.geometry(
            f"180x92+{self.app.settings.get('overlay_x', 40)}+{self.app.settings.get('overlay_y', 40)}"
        )
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-toolwindow", True)
        except Exception:
            pass
        self.root.configure(bg="#111827")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.label = tk.Label(
            self.root,
            text=f"{APP_NAME} OFF",
            fg="#ffffff",
            bg="#111827",
            font=("Segoe UI", 13, "bold"),
        )
        self.label.pack(pady=(14, 8))

        button = tk.Button(
            self.root,
            text="Toggle",
            command=lambda: self.app.toggle("overlay button"),
            relief="flat",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
        )
        button.pack(ipadx=16, ipady=4)

        self.running = True
        if self.app.settings.get("overlay_enabled"):
            self.visible = True
            self.root.deiconify()
        else:
            self.visible = False

        self._tick()
        self.root.mainloop()
        self.running = False

    def _tick(self):
        if not self.root:
            return

        state = "PAUSED" if self.app.network_paused else "READY"
        color = "#dc2626" if self.app.network_paused else "#16a34a"
        if self.label:
            self.label.configure(text=f"{APP_NAME} {state}", fg=color)

        self.root.after(500, self._tick)

    def show(self):
        self.visible = True
        if self.root:
            self.root.after(0, self.root.deiconify)

    def close(self):
        self.visible = False
        if self.root:
            self.root.after(0, self.root.withdraw)

    def stop(self):
        if self.root:
            self.root.after(0, self.root.destroy)


class LaxyControlApp:
    def __init__(self):
        self.settings = load_settings()
        self.network_paused = False
        self.service_running = True
        self.last_result = {"ok": True, "message": "Service started."}
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.httpd = None
        self.overlay = OverlayController(self)
        self.hotkeys = HotkeyManager(
            self.pause_network,
            self.restore_network,
            self.toggle,
            lambda message: self.set_last_result(False, message),
        )

    def set_last_result(self, ok, message, **extra):
        with self.lock:
            self.last_result = {"ok": bool(ok), "message": message, **extra}
        print(message)
        self.write_audit("result", ok=bool(ok), message=message, **extra)
        if ok and self.settings.get("show_notifications"):
            self.notify(message)

    def write_audit(self, event, **fields):
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        try:
            with AUDIT_LOG.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        except OSError:
            pass

    def notify(self, message):
        def worker():
            try:
                from win10toast import ToastNotifier

                ToastNotifier().show_toast(APP_NAME, message, duration=2, threaded=True)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def start(self):
        threading.Thread(target=network.prepare_fast_mode, daemon=True).start()
        self.start_server()
        self.reload_hotkeys()
        self.overlay.start()

        if self.settings.get("open_ui_on_start"):
            self.open_ui()

        self.set_last_result(True, f"{APP_NAME} service running at http://{HOST}:{PORT}")

    def start_server(self):
        handler = self.make_handler()
        self.httpd = ThreadingHTTPServer((HOST, PORT), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def reload_hotkeys(self):
        ok = self.hotkeys.start(
            self.settings.get("hotkey"),
            self.settings.get("mode"),
        )
        if ok:
            self.set_last_result(
                True,
                f"Hotkey bound: {self.settings.get('hotkey')}",
            )
        return ok

    def open_ui(self):
        webbrowser.open(f"http://{HOST}:{PORT}")

    def selected_adapter(self):
        return self.settings.get("adapter", "").strip()

    def pause_network(self, source="manual"):
        self.write_audit("action_requested", action="pause_network", source=source, adapter=self.selected_adapter())
        with self.lock:
            if self.network_paused:
                self.set_last_result(True, f"{APP_NAME} network already paused.", source=source)
                return self.last_result

        result = network.set_adapter_state(self.selected_adapter(), False)
        with self.lock:
            if result["ok"]:
                self.network_paused = True
        self.set_last_result(result["ok"], result["message"], source=source)
        return result

    def restore_network(self, source="manual"):
        self.write_audit("action_requested", action="restore_network", source=source, adapter=self.selected_adapter())
        result = network.set_adapter_state(self.selected_adapter(), True)
        with self.lock:
            if result["ok"]:
                self.network_paused = False
        self.set_last_result(result["ok"], result["message"], source=source)
        return result

    def toggle(self, source="manual"):
        self.write_audit("action_requested", action="toggle", source=source, adapter=self.selected_adapter())
        with self.lock:
            active = self.network_paused
        if active:
            return self.restore_network(source)
        return self.pause_network(source)

    def update_settings(self, data):
        with self.lock:
            updated = dict(self.settings)
            for key in (
                "hotkey",
                "mode",
                "adapter",
                "open_ui_on_start",
                "show_notifications",
                "overlay_enabled",
                "overlay_x",
                "overlay_y",
            ):
                if key in data:
                    updated[key] = data[key]
            self.settings = save_settings(updated)

        self.reload_hotkeys()
        if self.settings.get("overlay_enabled"):
            self.overlay.show()
        else:
            self.overlay.close()

        self.set_last_result(True, "Settings saved.")
        return self.settings

    def status(self):
        adapter = self.selected_adapter()
        return {
            "service_running": self.service_running,
            "is_admin": network.is_admin(),
            "settings": self.settings,
            "adapters": network.adapter_rows(),
            "selected_adapter_status": network.adapter_status(adapter),
            "network_paused": self.network_paused,
            "hotkeys_running": self.hotkeys.running,
            "overlay_visible": self.overlay.visible,
            "last_result": self.last_result,
        }

    def shutdown(self):
        self.service_running = False
        self.stop_event.set()
        with self.lock:
            active = self.network_paused
        if active:
            network.set_firewall_paused(False)
            with self.lock:
                self.network_paused = False
        self.hotkeys.stop()
        self.overlay.stop()
        if self.httpd:
            threading.Thread(target=self.httpd.shutdown, daemon=True).start()

    def make_handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def send_json(self, payload, status=200):
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def send_file(self, path):
                if not path.exists() or not path.is_file():
                    self.send_error(404)
                    return

                data = path.read_bytes()
                content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                if content_type.startswith("text/") or content_type in (
                    "application/javascript",
                    "application/json",
                ):
                    content_type = f"{content_type}; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def read_json(self):
                length = int(self.headers.get("Content-Length", "0"))
                if not length:
                    return {}
                return json.loads(self.rfile.read(length).decode("utf-8"))

            def do_GET(self):
                if self.path == "/api/status":
                    self.send_json(app.status())
                    return

                if self.path == "/api/open-ui":
                    app.open_ui()
                    self.send_json({"ok": True})
                    return

                requested = self.path.split("?", 1)[0]
                if requested in ("", "/"):
                    requested = "/index.html"
                safe = unquote(requested).lstrip("/")
                path = (WEB_ROOT / safe).resolve()
                if WEB_ROOT.resolve() not in path.parents and path != WEB_ROOT.resolve():
                    self.send_error(403)
                    return
                self.send_file(path)

            def do_POST(self):
                try:
                    data = self.read_json()
                except json.JSONDecodeError:
                    self.send_json({"ok": False, "message": "Invalid JSON."}, status=400)
                    return

                if self.path == "/api/settings":
                    self.send_json({"ok": True, "settings": app.update_settings(data)})
                    return

                if self.path == "/api/action":
                    action = data.get("action")
                    if action == "restore":
                        self.send_json(app.restore_network("web"))
                    elif action == "pause":
                        self.send_json(app.pause_network("web"))
                    elif action == "toggle":
                        self.send_json(app.toggle("web"))
                    elif action == "show_overlay":
                        app.overlay.show()
                        self.send_json({"ok": True, "message": "Overlay shown."})
                    elif action == "close_overlay":
                        app.overlay.close()
                        self.send_json({"ok": True, "message": "Overlay closed."})
                    elif action == "open_ui":
                        app.open_ui()
                        self.send_json({"ok": True, "message": "Web UI opened."})
                    elif action == "shutdown":
                        self.send_json({"ok": True, "message": "Service stopping."})
                        app.shutdown()
                    else:
                        self.send_json({"ok": False, "message": "Unknown action."}, status=400)
                    return

                self.send_error(404)

            def log_message(self, format, *args):
                return

        return Handler


def main():
    if not acquire_single_instance():
        if wait_for_service():
            webbrowser.open(f"http://{HOST}:{PORT}")
        return

    if service_is_running():
        webbrowser.open(f"http://{HOST}:{PORT}")
        return

    app = LaxyControlApp()

    def handle_signal(signum, frame):
        app.shutdown()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    app.start()
    while not app.stop_event.is_set():
        time.sleep(0.25)


if __name__ == "__main__":
    main()
