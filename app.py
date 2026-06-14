from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlencode, unquote, urlparse
import ctypes
import json
import mimetypes
import os
import secrets
import signal
import socket
import subprocess
import sys
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
UI_TOKEN_FILE = APP_DIR / ".secure-ui-token"
MAX_PAUSE_SECONDS = 3.0
MUTEX_HANDLE = None


def write_ui_token(token):
    try:
        UI_TOKEN_FILE.write_text(token, encoding="utf-8")
    except OSError:
        pass


def read_ui_token():
    try:
        return UI_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def secure_ui_url(token):
    url = f"http://{HOST}:{PORT}"
    if token:
        return f"{url}/?{urlencode({'ui_token': token})}"
    return url


def launch_secure_browser(url, allowed_hosts):
    allowed = ",".join(str(host).strip() for host in allowed_hosts if str(host).strip())
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--secure-browser", url, allowed]
    else:
        command = [sys.executable, str(Path(__file__).resolve()), "--secure-browser", url, allowed]

    return subprocess.Popen(command, cwd=str(APP_DIR), close_fds=True)


def launch_overlay_process(token, x, y):
    url = f"http://{HOST}:{PORT}"
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--overlay", url, token, str(x), str(y)]
    else:
        command = [sys.executable, str(Path(__file__).resolve()), "--overlay", url, token, str(x), str(y)]

    return subprocess.Popen(command, cwd=str(APP_DIR), close_fds=True)


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
        self.process = None
        self.visible = False

    def start(self):
        if self.app.settings.get("overlay_enabled"):
            self.show()
        return True

    def show(self):
        if self.process and self.process.poll() is None:
            self.visible = True
            return

        self.process = launch_overlay_process(
            self.app.ui_token if self.app.settings.get("secure_browser_enabled") else "",
            self.app.settings.get("overlay_x", 40),
            self.app.settings.get("overlay_y", 40),
        )
        self.visible = True

    def close(self):
        self.visible = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.process = None

    def stop(self):
        self.close()


class LaxyControlApp:
    def __init__(self):
        self.settings = load_settings()
        self.ui_token = secrets.token_urlsafe(32)
        write_ui_token(self.ui_token)
        self.network_paused = False
        self.pause_generation = 0
        self.pause_timer = None
        self.service_running = True
        self.last_result = {"ok": True, "message": "Service started."}
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.httpd = None
        self.ui_process = None
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
        url = secure_ui_url(self.ui_token if self.settings.get("secure_browser_enabled") else "")
        if self.settings.get("secure_browser_enabled"):
            with self.lock:
                if self.ui_process and self.ui_process.poll() is None:
                    return
                self.ui_process = launch_secure_browser(
                    url,
                    self.settings.get("secure_browser_allowed_hosts"),
                )
            return
        webbrowser.open(url)

    def selected_adapter(self):
        return self.settings.get("adapter", "").strip()

    def restore_delay_seconds(self):
        try:
            return float(self.settings.get("restore_delay_seconds", MAX_PAUSE_SECONDS))
        except (TypeError, ValueError):
            return MAX_PAUSE_SECONDS

    def cancel_pause_timer(self):
        if self.pause_timer:
            self.pause_timer.cancel()
            self.pause_timer = None

    def schedule_pause_timeout(self):
        self.cancel_pause_timer()
        generation = self.pause_generation
        timer = threading.Timer(self.restore_delay_seconds(), self.restore_after_pause_timeout, args=(generation,))
        timer.daemon = True
        self.pause_timer = timer
        timer.start()

    def restore_after_pause_timeout(self, generation):
        with self.lock:
            if not self.network_paused or generation != self.pause_generation:
                return

        self.write_audit(
            "pause_timeout",
            seconds=self.restore_delay_seconds(),
            adapter=self.selected_adapter(),
        )
        self.restore_network(f"auto restore after {self.restore_delay_seconds():g}s limit")

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
                self.pause_generation += 1
                self.schedule_pause_timeout()
        self.set_last_result(result["ok"], result["message"], source=source)
        return result

    def restore_network(self, source="manual"):
        self.write_audit("action_requested", action="restore_network", source=source, adapter=self.selected_adapter())
        result = network.set_adapter_state(self.selected_adapter(), True)
        with self.lock:
            if result["ok"]:
                self.network_paused = False
                self.pause_generation += 1
                self.cancel_pause_timer()
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
            old_restore_delay = self.restore_delay_seconds()
            for key in (
                "hotkey",
                "mode",
                "adapter",
                "open_ui_on_start",
                "show_notifications",
                "overlay_enabled",
                "overlay_x",
                "overlay_y",
                "restore_delay_seconds",
            ):
                if key in data:
                    updated[key] = data[key]
            self.settings = save_settings(updated)
            restore_delay_changed = self.restore_delay_seconds() != old_restore_delay
            network_paused = self.network_paused

        self.reload_hotkeys()
        if restore_delay_changed and network_paused:
            self.schedule_pause_timeout()
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
            "max_pause_seconds": self.restore_delay_seconds(),
            "hotkeys_running": self.hotkeys.running,
            "hotkey_backend": self.hotkeys.backend,
            "overlay_visible": self.overlay.visible,
            "last_result": self.last_result,
        }

    def shutdown(self):
        self.service_running = False
        self.stop_event.set()
        self.cancel_pause_timer()
        with self.lock:
            active = self.network_paused
        if active:
            network.set_firewall_paused(False)
            with self.lock:
                self.network_paused = False
        self.hotkeys.stop()
        self.overlay.stop()
        if self.ui_process and self.ui_process.poll() is None:
            self.ui_process.terminate()
        self.ui_process = None
        if read_ui_token() == self.ui_token:
            try:
                UI_TOKEN_FILE.unlink()
            except OSError:
                pass
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
                self.maybe_set_ui_cookie()
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
                self.maybe_set_ui_cookie()
                self.end_headers()
                self.wfile.write(data)

            def parsed_path(self):
                return urlparse(self.path)

            def request_ui_token(self):
                query = parse_qs(self.parsed_path().query)
                token = query.get("ui_token", [""])[0]
                if token:
                    return token

                cookie = SimpleCookie()
                cookie.load(self.headers.get("Cookie", ""))
                morsel = cookie.get("laxy_ui_token")
                return morsel.value if morsel else ""

            def ui_authorized(self):
                if not app.settings.get("secure_browser_enabled"):
                    return True
                return secrets.compare_digest(self.request_ui_token(), app.ui_token)

            def maybe_set_ui_cookie(self):
                parsed = self.parsed_path()
                query_token = parse_qs(parsed.query).get("ui_token", [""])[0]
                if query_token and secrets.compare_digest(query_token, app.ui_token):
                    self.send_header(
                        "Set-Cookie",
                        f"laxy_ui_token={app.ui_token}; Path=/; SameSite=Strict; HttpOnly",
                    )

            def read_json(self):
                length = int(self.headers.get("Content-Length", "0"))
                if not length:
                    return {}
                return json.loads(self.rfile.read(length).decode("utf-8"))

            def do_GET(self):
                if not self.ui_authorized():
                    self.send_error(403)
                    return

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
                if not self.ui_authorized():
                    self.send_error(403)
                    return

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
    if len(sys.argv) > 1 and sys.argv[1] == "--secure-browser":
        from secure_browser import run_secure_browser

        target_url = sys.argv[2] if len(sys.argv) > 2 else f"http://{HOST}:{PORT}"
        allowed_hosts = []
        if len(sys.argv) > 3:
            allowed_hosts = [host for host in sys.argv[3].split(",") if host.strip()]
        raise SystemExit(run_secure_browser(target_url, allowed_hosts))

    if len(sys.argv) > 1 and sys.argv[1] == "--overlay":
        from overlay_window import run_overlay

        base_url = sys.argv[2] if len(sys.argv) > 2 else f"http://{HOST}:{PORT}"
        token = sys.argv[3] if len(sys.argv) > 3 else ""
        try:
            x = int(sys.argv[4]) if len(sys.argv) > 4 else 40
            y = int(sys.argv[5]) if len(sys.argv) > 5 else 40
        except ValueError:
            x, y = 40, 40
        raise SystemExit(run_overlay(base_url, token, x, y))

    if not acquire_single_instance():
        if wait_for_service():
            settings = load_settings()
            if settings.get("secure_browser_enabled"):
                launch_secure_browser(secure_ui_url(read_ui_token()), settings.get("secure_browser_allowed_hosts"))
            else:
                webbrowser.open(f"http://{HOST}:{PORT}")
        return

    if service_is_running():
        settings = load_settings()
        if settings.get("secure_browser_enabled"):
            launch_secure_browser(secure_ui_url(read_ui_token()), settings.get("secure_browser_allowed_hosts"))
        else:
            webbrowser.open(f"http://{HOST}:{PORT}")
        return

    app = LaxyControlApp()

    def handle_signal(signum, frame):
        app.shutdown()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    app.start()
    if sys.platform == "win32":
        from tray_controller import run_tray

        run_tray(app)
    else:
        while not app.stop_event.is_set():
            time.sleep(0.25)


if __name__ == "__main__":
    main()
