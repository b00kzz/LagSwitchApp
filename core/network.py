import ctypes
import csv
import heapq
import os
import random
import re
import subprocess
import sys
import threading
import time
import winreg
from functools import lru_cache
from io import StringIO


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FIREWALL_GROUP = "LaxyControl Rules"
APP_FIREWALL_GROUP = "LaxyControl App Rules"
FIREWALL_OUT_RULE = "LaxyControl Pause Outbound"
FIREWALL_IN_RULE = "LaxyControl Pause Inbound"
APP_FIREWALL_OUT_RULE = "LaxyControl App Pause Outbound"
APP_FIREWALL_IN_RULE = "LaxyControl App Pause Inbound"
FIREWALL_READY = False
APP_FIREWALL_PATH = ""
LOCAL_FIREWALL_RULES_ALLOWED = None
LAG_ENGINE = None
LAG_PROFILE = {}
LAG_ENABLED = False


def _completed(ok=True, message="", returncode=0, **extra):
    return {
        "ok": ok,
        "message": message,
        "returncode": returncode,
        **extra,
    }


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_netsh(*args):
    return subprocess.run(
        ["netsh", *args],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
        text=True,
    )


def _candidate_windivert_paths():
    names = ("WinDivert.dll", "windivert.dll")
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roots = [
        app_root,
        os.path.join(app_root, "tools"),
        os.path.join(app_root, "tools", "windivert"),
        os.path.join(app_root, "tools", "windivert", "x64"),
        os.path.join(app_root, "tools", "windivert", "x86"),
        os.path.join(app_root, "bin"),
    ]
    if getattr(sys, "frozen", False):
        roots.append(os.path.dirname(sys.executable))
    bundle_root = getattr(sys, "_MEIPASS", "")
    if bundle_root:
        roots.append(bundle_root)

    for root in roots:
        for name in names:
            yield os.path.join(root, name)


def traffic_shaper_path():
    for candidate in _candidate_windivert_paths():
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return ""


def traffic_shaper_available():
    return bool(traffic_shaper_path())


def _lag_engine_running():
    return LAG_ENGINE is not None and LAG_ENGINE.is_running()


def lag_active():
    return _lag_engine_running() and LAG_ENABLED


def active_lag_profile():
    if not lag_active():
        return {}
    return dict(LAG_PROFILE)


def _clamped_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))


def _normalized_lag_profile(profile):
    profile = profile or {}
    delay_ms = int(_clamped_float(profile.get("delay_ms"), 120, 0, 5000))
    jitter_ms = int(_clamped_float(profile.get("jitter_ms"), 30, 0, 5000))
    loss_percent = _clamped_float(profile.get("loss_percent"), 4.0, 0.0, 100.0)
    filter_text = str(profile.get("filter") or "ip").strip() or "ip"
    return {
        "delay_ms": delay_ms,
        "jitter_ms": jitter_ms,
        "loss_percent": loss_percent,
        "filter": filter_text,
    }


class WinDivertLagEngine:
    WINDIVERT_LAYER_NETWORK = 0
    WINDIVERT_PRIORITY_DEFAULT = 0
    WINDIVERT_FLAG_DEFAULT = 0
    MAX_PACKET_SIZE = 0xFFFF
    ADDRESS_SIZE = 128

    def __init__(self, dll_path, profile, enabled=True):
        self.dll_path = dll_path
        self.profile = dict(profile)
        self.dll = None
        self.handle = None
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.error = ""
        self.recv_thread = None
        self.send_thread = None
        self.profile_lock = threading.Lock()
        self.enabled = bool(enabled)
        self.condition = threading.Condition()
        self.queue = []
        self.sequence = 0

    def start(self):
        self.dll = ctypes.WinDLL(self.dll_path, use_last_error=True)
        self._bind_api()
        self.handle = self.dll.WinDivertOpen(
            self.profile["filter"].encode("utf-8"),
            self.WINDIVERT_LAYER_NETWORK,
            self.WINDIVERT_PRIORITY_DEFAULT,
            self.WINDIVERT_FLAG_DEFAULT,
        )
        invalid = ctypes.c_void_p(-1).value
        if not self.handle or self.handle == invalid:
            code = ctypes.get_last_error()
            raise OSError(code, "WinDivertOpen failed. Run as Administrator and keep WinDivert.dll/WinDivert64.sys together.")

        self.recv_thread = threading.Thread(target=self._recv_loop, name="LaxyControlLagRecv", daemon=True)
        self.send_thread = threading.Thread(target=self._send_loop, name="LaxyControlLagSend", daemon=True)
        self.recv_thread.start()
        self.send_thread.start()
        self.ready_event.set()

    def _bind_api(self):
        self.dll.WinDivertOpen.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int16, ctypes.c_uint64]
        self.dll.WinDivertOpen.restype = ctypes.c_void_p
        self.dll.WinDivertRecv.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.c_void_p,
        ]
        self.dll.WinDivertRecv.restype = ctypes.c_bool
        self.dll.WinDivertSend.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.c_void_p,
        ]
        self.dll.WinDivertSend.restype = ctypes.c_bool
        self.dll.WinDivertClose.argtypes = [ctypes.c_void_p]
        self.dll.WinDivertClose.restype = ctypes.c_bool

    def is_running(self):
        return self.ready_event.is_set() and not self.stop_event.is_set()

    def set_enabled(self, enabled, profile=None):
        with self.profile_lock:
            self.enabled = bool(enabled)
            if profile is not None:
                self.profile = dict(profile)
        if not enabled:
            with self.condition:
                self.queue.clear()
                self.condition.notify_all()

    def state_snapshot(self):
        with self.profile_lock:
            return self.enabled, dict(self.profile)

    def stop(self):
        self.stop_event.set()
        if self.handle:
            try:
                self.dll.WinDivertClose(self.handle)
            except Exception:
                pass
            self.handle = None
        with self.condition:
            self.condition.notify_all()
        for thread in (self.recv_thread, self.send_thread):
            if thread and thread.is_alive():
                thread.join(timeout=1.5)

    def _packet_delay_seconds(self, profile):
        delay_ms = int(profile.get("delay_ms", 0))
        jitter_ms = int(profile.get("jitter_ms", 0))
        if jitter_ms:
            delay_ms = max(0, delay_ms + random.randint(-jitter_ms, jitter_ms))
        return delay_ms / 1000.0

    def _should_drop(self, profile):
        loss_percent = float(profile.get("loss_percent", 0.0))
        return loss_percent > 0 and random.random() < (loss_percent / 100.0)

    def _recv_loop(self):
        packet = ctypes.create_string_buffer(self.MAX_PACKET_SIZE)
        while not self.stop_event.is_set():
            addr = ctypes.create_string_buffer(self.ADDRESS_SIZE)
            read_len = ctypes.c_uint(0)
            ok = self.dll.WinDivertRecv(self.handle, packet, self.MAX_PACKET_SIZE, ctypes.byref(read_len), addr)
            if not ok:
                if not self.stop_event.is_set():
                    self.error = f"WinDivertRecv failed: {ctypes.get_last_error()}"
                    self.stop_event.set()
                break

            enabled, profile = self.state_snapshot()
            if enabled and self._should_drop(profile):
                continue

            data = bytes(packet.raw[: read_len.value])
            address = bytes(addr.raw)
            delay_seconds = self._packet_delay_seconds(profile) if enabled else 0
            send_at = time.monotonic() + delay_seconds
            with self.condition:
                self.sequence += 1
                heapq.heappush(self.queue, (send_at, self.sequence, data, address))
                self.condition.notify()

    def _send_loop(self):
        while not self.stop_event.is_set():
            with self.condition:
                while not self.queue and not self.stop_event.is_set():
                    self.condition.wait(timeout=0.2)
                if self.stop_event.is_set():
                    break
                send_at, _, data, address = self.queue[0]
                wait_seconds = send_at - time.monotonic()
                if wait_seconds > 0:
                    self.condition.wait(timeout=min(wait_seconds, 0.2))
                    continue
                heapq.heappop(self.queue)

            packet = ctypes.create_string_buffer(data, len(data))
            addr = ctypes.create_string_buffer(address, len(address))
            send_len = ctypes.c_uint(0)
            self.dll.WinDivertSend(self.handle, packet, len(data), ctypes.byref(send_len), addr)


def set_lag_state(active, profile=None):
    global LAG_ENGINE, LAG_PROFILE, LAG_ENABLED

    if active:
        lag_profile = _normalized_lag_profile(profile)
        if lag_profile["delay_ms"] <= 0 and lag_profile["jitter_ms"] <= 0 and lag_profile["loss_percent"] <= 0:
            return _completed(False, "Set delay, jitter, or packet loss above zero before starting lag.", returncode=1)

        if _lag_engine_running() and LAG_ENGINE.profile.get("filter") == lag_profile["filter"]:
            LAG_ENGINE.set_enabled(True, lag_profile)
            LAG_PROFILE = lag_profile
            LAG_ENABLED = True
            return _completed(
                True,
                (
                    "Lag started instantly: "
                    f"{lag_profile['delay_ms']}ms delay, "
                    f"{lag_profile['jitter_ms']}ms jitter, "
                    f"{lag_profile['loss_percent']:g}% packet loss."
                ),
                method="windivert",
                profile=lag_profile,
            )

        if _lag_engine_running():
            LAG_ENGINE.stop()
            LAG_ENGINE = None
            LAG_PROFILE = {}
            LAG_ENABLED = False

        dll_path = traffic_shaper_path()
        if not dll_path:
            return _completed(
                False,
                "WinDivert not found. Put WinDivert.dll and WinDivert64.sys next to LaxyControl.exe or in tools\\windivert\\.",
                returncode=2,
                method="windivert",
            )

        engine = WinDivertLagEngine(dll_path, lag_profile)
        try:
            engine.start()
        except OSError as exc:
            LAG_ENGINE = None
            LAG_PROFILE = {}
            LAG_ENABLED = False
            return _completed(False, f"Could not start WinDivert lag engine: {exc}", returncode=1, method="windivert")

        LAG_ENGINE = engine
        LAG_PROFILE = lag_profile
        LAG_ENABLED = True
        return _completed(
            True,
            (
                "Lag started: "
                f"{lag_profile['delay_ms']}ms delay, "
                f"{lag_profile['jitter_ms']}ms jitter, "
                f"{lag_profile['loss_percent']:g}% packet loss."
            ),
            method="windivert",
            profile=lag_profile,
        )

    if not _lag_engine_running():
        if LAG_ENGINE:
            LAG_ENGINE.stop()
        LAG_ENGINE = None
        LAG_PROFILE = {}
        LAG_ENABLED = False
        return _completed(True, "Lag is already stopped.", method="windivert")

    LAG_ENGINE.set_enabled(False)
    LAG_PROFILE = {}
    LAG_ENABLED = False
    return _completed(True, "Lag stopped instantly.", method="windivert")


def shutdown_lag_engine():
    global LAG_ENGINE, LAG_PROFILE, LAG_ENABLED
    if LAG_ENGINE:
        LAG_ENGINE.stop()
    LAG_ENGINE = None
    LAG_PROFILE = {}
    LAG_ENABLED = False


def local_firewall_rules_allowed():
    global LOCAL_FIREWALL_RULES_ALLOWED
    if LOCAL_FIREWALL_RULES_ALLOWED is not None:
        return LOCAL_FIREWALL_RULES_ALLOWED

    policy_profiles = ("DomainProfile", "PrivateProfile", "PublicProfile")
    policy_root = r"SOFTWARE\Policies\Microsoft\WindowsFirewall"
    for profile in policy_profiles:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"{policy_root}\{profile}") as key:
                value, _ = winreg.QueryValueEx(key, "AllowLocalPolicyMerge")
        except FileNotFoundError:
            continue
        except OSError:
            continue

        if int(value) == 0:
            LOCAL_FIREWALL_RULES_ALLOWED = False
            return LOCAL_FIREWALL_RULES_ALLOWED

    LOCAL_FIREWALL_RULES_ALLOWED = True
    return LOCAL_FIREWALL_RULES_ALLOWED


def _firewall_rule_exists(rule_name):
    result = _run_netsh("advfirewall", "firewall", "show", "rule", f"name={rule_name}")
    return result.returncode == 0 and rule_name.lower() in result.stdout.lower()


def _firewall_rule_enabled(rule_name):
    result = _run_netsh("advfirewall", "firewall", "show", "rule", f"name={rule_name}", "verbose")
    if result.returncode != 0:
        return False

    for line in result.stdout.splitlines():
        if line.strip().lower().startswith("enabled:"):
            return line.split(":", 1)[1].strip().lower() == "yes"

    return False


def _add_firewall_rule(rule_name, direction):
    return _run_netsh(
        "advfirewall",
        "firewall",
        "add",
        "rule",
        f"name={rule_name}",
        f"dir={direction}",
        "action=block",
        "enable=no",
        "profile=any",
        "program=any",
        "protocol=any",
    )


def _delete_firewall_rule(rule_name):
    return _run_netsh("advfirewall", "firewall", "delete", "rule", f"name={rule_name}")


def _add_app_firewall_rule(rule_name, direction, app_path):
    return _run_netsh(
        "advfirewall",
        "firewall",
        "add",
        "rule",
        f"name={rule_name}",
        f"dir={direction}",
        "action=block",
        "enable=no",
        "profile=any",
        f"program={app_path}",
        "protocol=any",
    )


def _ensure_firewall_rules():
    global FIREWALL_READY
    if FIREWALL_READY:
        return subprocess.CompletedProcess(args=["netsh"], returncode=0, stdout="", stderr="")

    for rule_name, direction in ((FIREWALL_OUT_RULE, "out"), (FIREWALL_IN_RULE, "in")):
        if _firewall_rule_exists(rule_name):
            continue

        result = _add_firewall_rule(rule_name, direction)
        if result.returncode != 0:
            return result

    FIREWALL_READY = True
    return subprocess.CompletedProcess(args=["netsh"], returncode=0, stdout="", stderr="")


def _ensure_app_firewall_rules(app_path):
    global APP_FIREWALL_PATH
    normalized_path = os.path.abspath(app_path.strip().strip('"')) if app_path else ""
    if not normalized_path:
        return subprocess.CompletedProcess(
            args=["netsh"],
            returncode=1,
            stdout="",
            stderr="No application selected.",
        )

    if not local_firewall_rules_allowed():
        return subprocess.CompletedProcess(
            args=["netsh"],
            returncode=1,
            stdout="",
            stderr="Local firewall rules are disabled by Windows policy, so per-app blocking cannot work on this machine.",
        )

    if APP_FIREWALL_PATH.lower() == normalized_path.lower():
        ready = all(_firewall_rule_exists(rule_name) for rule_name in (APP_FIREWALL_OUT_RULE, APP_FIREWALL_IN_RULE))
        if ready:
            return subprocess.CompletedProcess(args=["netsh"], returncode=0, stdout="", stderr="")

    for rule_name in (APP_FIREWALL_OUT_RULE, APP_FIREWALL_IN_RULE):
        _delete_firewall_rule(rule_name)

    for rule_name, direction in ((APP_FIREWALL_OUT_RULE, "out"), (APP_FIREWALL_IN_RULE, "in")):
        result = _add_app_firewall_rule(rule_name, direction, normalized_path)
        if result.returncode != 0:
            APP_FIREWALL_PATH = ""
            return result

    APP_FIREWALL_PATH = normalized_path
    return subprocess.CompletedProcess(args=["netsh"], returncode=0, stdout="", stderr="")


def prepare_fast_mode():
    global LAG_ENGINE, LAG_PROFILE, LAG_ENABLED

    if _lag_engine_running():
        return True

    dll_path = traffic_shaper_path()
    if not dll_path:
        return False

    profile = _normalized_lag_profile({"delay_ms": 0, "jitter_ms": 0, "loss_percent": 0, "filter": "ip"})
    engine = WinDivertLagEngine(dll_path, profile, enabled=False)
    try:
        engine.start()
    except OSError:
        return False

    LAG_ENGINE = engine
    LAG_PROFILE = {}
    LAG_ENABLED = False
    return True


def ping_diagnostics(target="1.1.1.1", count=4, timeout_ms=1200):
    target = str(target or "1.1.1.1").strip()
    if not re.fullmatch(r"[A-Za-z0-9.\-:]{1,253}", target):
        return _completed(False, "Use a hostname or IP address only.", returncode=1)

    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 4
    count = min(10, max(1, count))

    try:
        timeout_ms = int(timeout_ms)
    except (TypeError, ValueError):
        timeout_ms = 1200
    timeout_ms = min(5000, max(300, timeout_ms))

    try:
        result = subprocess.run(
            ["ping", "-n", str(count), "-w", str(timeout_ms), target],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            text=True,
            timeout=max(4, (timeout_ms / 1000 * count) + 2),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _completed(False, f"Ping diagnostic failed: {exc}", returncode=1, target=target)

    output = (result.stdout or "") + "\n" + (result.stderr or "")
    times = [int(value) for value in re.findall(r"time[=<]\s*(\d+)\s*ms", output, flags=re.IGNORECASE)]
    loss_match = re.search(r"\((\d+(?:\.\d+)?)%\s*loss\)", output, flags=re.IGNORECASE)
    average_match = re.search(r"Average\s*=\s*(\d+)\s*ms", output, flags=re.IGNORECASE)

    received = len(times)
    sent = count
    loss_percent = float(loss_match.group(1)) if loss_match else round(((sent - received) / sent) * 100, 1)
    average_ms = int(average_match.group(1)) if average_match else (round(sum(times) / received) if received else None)
    jitter_ms = round(max(times) - min(times), 1) if len(times) > 1 else 0

    return _completed(
        result.returncode == 0 or received > 0,
        "Diagnostic complete." if received else "Diagnostic complete, but no replies were received.",
        returncode=result.returncode,
        target=target,
        sent=sent,
        received=received,
        loss_percent=loss_percent,
        average_ms=average_ms,
        jitter_ms=jitter_ms,
        samples_ms=times,
    )


def _set_firewall_rules_enabled(paused, rule_names):
    enabled = "yes" if paused else "no"
    return [
        _run_netsh(
            "advfirewall",
            "firewall",
            "set",
            "rule",
            f"name={rule_name}",
            "new",
            f"enable={enabled}",
        )
        for rule_name in rule_names
    ]


def set_firewall_paused(paused, app_path=None):
    if app_path:
        ensure = _ensure_app_firewall_rules(app_path)
        rule_names = (APP_FIREWALL_OUT_RULE, APP_FIREWALL_IN_RULE)
        method = "app_firewall"
        target = os.path.abspath(app_path.strip().strip('"')) if app_path else ""
    else:
        ensure = _ensure_firewall_rules()
        rule_names = (FIREWALL_OUT_RULE, FIREWALL_IN_RULE)
        method = "firewall"
        target = ""

    if ensure.returncode != 0:
        return {
            "ok": False,
            "message": (ensure.stderr or ensure.stdout or "Could not prepare firewall rules.").strip(),
            "returncode": ensure.returncode,
        }

    results = _set_firewall_rules_enabled(paused, rule_names)

    failed = next((result for result in results if result.returncode != 0), None)
    if failed:
        return {
            "ok": False,
            "message": (failed.stderr or failed.stdout or "Could not update firewall rules.").strip(),
            "returncode": failed.returncode,
        }

    action = "paused" if paused else "restored"
    target_message = f" for {target}" if target else ""
    return {
        "ok": True,
        "message": f"Network access {action}{target_message} with local firewall rules.",
        "returncode": 0,
        "method": method,
        "app_path": target,
    }


def _csv_rows(command_text, timeout=8):
    command = ["powershell", "-NoProfile", "-Command", command_text]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    return list(csv.DictReader(StringIO(result.stdout)))


def _clean_app_path(path):
    value = str(path or "").strip().strip('"')
    if not value:
        return ""
    if "," in value and value.lower().endswith((".exe,0", ".exe,1")):
        value = value.rsplit(",", 1)[0]
    if value.lower().endswith(".exe") and os.path.isfile(value):
        return os.path.abspath(value)
    return ""


def _append_app(rows, seen, name, path, source, pid="", window_title=""):
    normalized_path = _clean_app_path(path)
    app_name = str(name or "").strip()
    if not normalized_path or not app_name:
        return

    key = normalized_path.lower()
    existing = seen.get(key)
    if existing:
        sources = set(existing["source"].split(", "))
        sources.add(source)
        existing["source"] = ", ".join(sorted(sources))
        if pid:
            pids = {part.strip() for part in existing.get("pid", "").split(",") if part.strip()}
            pids.add(str(pid).strip())
            existing["pid"] = ", ".join(sorted(pids, key=lambda value: int(value) if value.isdigit() else value))
        if window_title:
            titles = {part.strip() for part in existing.get("window_title", "").split(" | ") if part.strip()}
            titles.add(str(window_title).strip())
            existing["window_title"] = " | ".join(sorted(titles))
        if existing["name"].lower().endswith(".exe") and not app_name.lower().endswith(".exe"):
            existing["name"] = app_name
        return

    row = {
        "name": app_name,
        "pid": str(pid or "").strip(),
        "path": normalized_path,
        "source": source,
        "window_title": str(window_title or "").strip(),
    }
    rows.append(row)
    seen[key] = row


def _running_app_rows():
    command_texts = [
        (
            "Get-Process | Where-Object { $_.Path } | "
            "Select-Object @{Name='ProcessId';Expression={$_.Id}},"
            "@{Name='Name';Expression={$_.ProcessName + '.exe'}},"
            "@{Name='ExecutablePath';Expression={$_.Path}},"
            "@{Name='WindowTitle';Expression={$_.MainWindowTitle}} | ConvertTo-Csv -NoTypeInformation"
        ),
        (
            "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath } | "
            "Select-Object ProcessId,Name,ExecutablePath,@{Name='WindowTitle';Expression={''}} | "
            "ConvertTo-Csv -NoTypeInformation"
        ),
    ]

    combined = []
    seen = set()
    for command_text in command_texts:
        for row in _csv_rows(command_text):
            key = (
                str(row.get("ProcessId") or "").strip(),
                str(row.get("ExecutablePath") or "").strip().lower(),
            )
            if not key[1] or key in seen:
                continue
            seen.add(key)
            combined.append(row)

    return combined


def _shortcut_app_rows():
    try:
        import win32com.client
    except Exception:
        return []

    roots = [
        os.path.join(os.environ.get("ProgramData", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("PUBLIC", ""), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
    ]

    shell = win32com.client.Dispatch("WScript.Shell")
    rows = []
    seen = set()
    for root in roots:
        if not root or not os.path.isdir(root):
            continue

        for current_root, _, files in os.walk(root):
            for filename in files:
                if not filename.lower().endswith(".lnk"):
                    continue

                shortcut_path = os.path.join(current_root, filename)
                try:
                    shortcut = shell.CreateShortcut(shortcut_path)
                    target = _clean_app_path(shortcut.TargetPath)
                except Exception:
                    continue

                if not target:
                    continue

                key = (os.path.splitext(filename)[0].lower(), target.lower())
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "ProcessId": "",
                        "Name": os.path.splitext(filename)[0],
                        "ExecutablePath": target,
                        "WindowTitle": "",
                        "Source": "shortcut",
                    }
                )

    return rows


def _installed_app_rows():
    command_text = (
        "$paths = @("
        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*', "
        "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*', "
        "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*'"
        "); "
        "$items = foreach ($path in $paths) { "
        "Get-ItemProperty -Path $path -ErrorAction SilentlyContinue | ForEach-Object { "
        "$display = [string]$_.DisplayName; "
        "$icon = [string]$_.DisplayIcon; "
        "if (-not $display -or -not $icon) { return }; "
        "$candidate = $icon.Trim('\"'); "
        "if ($candidate -match '^(.*?\\.exe)') { $candidate = $Matches[1] }; "
        "if ($candidate -and (Test-Path $candidate)) { "
        "[pscustomobject]@{ ProcessId=''; Name=$display; ExecutablePath=$candidate; WindowTitle=''; Source='installed' } "
        "} "
        "} "
        "}; "
        "$items | Sort-Object Name,ExecutablePath -Unique | ConvertTo-Csv -NoTypeInformation"
    )
    return _csv_rows(command_text)


def app_rows():
    rows = []
    seen = {}

    for row in _running_app_rows():
        _append_app(
            rows,
            seen,
            row.get("WindowTitle") or row.get("Name"),
            row.get("ExecutablePath"),
            "running",
            row.get("ProcessId"),
            row.get("WindowTitle"),
        )

    for row in _shortcut_app_rows():
        _append_app(rows, seen, row.get("Name"), row.get("ExecutablePath"), row.get("Source") or "shortcut")

    for row in _installed_app_rows():
        _append_app(rows, seen, row.get("Name"), row.get("ExecutablePath"), row.get("Source") or "installed")

    for row in rows:
        search_parts = [
            row.get("name", ""),
            row.get("window_title", ""),
            row.get("pid", ""),
            row.get("path", ""),
            os.path.basename(row.get("path", "")),
            row.get("source", ""),
        ]
        row["search"] = " ".join(part for part in search_parts if part).lower()

    def sort_key(item):
        source = item.get("source", "")
        priority = 0 if "running" in source else 1 if "shortcut" in source else 2
        return (priority, item["name"].lower(), item["path"].lower())

    return sorted(rows, key=sort_key)


@lru_cache(maxsize=128)
def app_icon_png(app_path):
    normalized_path = os.path.abspath(app_path.strip().strip('"')) if app_path else ""
    if not normalized_path or not os.path.isfile(normalized_path):
        return None

    command_text = (
        "& { param([string]$Path) "
        "Add-Type -AssemblyName System.Drawing; "
        "$icon = [System.Drawing.Icon]::ExtractAssociatedIcon($Path); "
        "if ($null -eq $icon) { exit 2 }; "
        "$bitmap = $icon.ToBitmap(); "
        "$stream = New-Object System.IO.MemoryStream; "
        "$bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png); "
        "$bytes = $stream.ToArray(); "
        "[Console]::OpenStandardOutput().Write($bytes, 0, $bytes.Length); "
        "$stream.Dispose(); $bitmap.Dispose(); $icon.Dispose(); "
        "}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command_text, normalized_path],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
        timeout=5,
    )
    if result.returncode != 0 or not result.stdout:
        return None
    return result.stdout

def adapter_rows():
    result = _run_netsh("interface", "show", "interface")
    rows = []

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("Admin State") or line.startswith("-"):
            continue

        parts = line.split(None, 3)
        if len(parts) != 4:
            continue

        rows.append(
            {
                "admin_state": parts[0],
                "state": parts[1],
                "type": parts[2],
                "name": parts[3],
            }
        )

    return rows


def adapter_status(adapter_name):
    if not adapter_name:
        return None

    for row in adapter_rows():
        if row["name"].lower() == adapter_name.lower():
            return row

    return None


def app_firewall_paused(app_path):
    return False


def set_adapter_state(adapter_name, enabled, app_path=None):
    result = set_lag_state(not enabled)
    return {
        **result,
        "adapter": adapter_name,
        "enabled": enabled,
        "app_path": app_path or "",
    }
