import ctypes
import csv
import os
import subprocess
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
    return _ensure_firewall_rules().returncode == 0


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
    if not app_path:
        return False
    return _firewall_rule_enabled(APP_FIREWALL_OUT_RULE) or _firewall_rule_enabled(APP_FIREWALL_IN_RULE)


def set_adapter_state(adapter_name, enabled, app_path=None):
    if not adapter_name and not app_path:
        return {
            "ok": False,
            "message": "No adapter selected.",
            "adapter": adapter_name,
            "enabled": enabled,
        }

    if app_path:
        firewall_result = set_firewall_paused(not enabled, app_path)
        return {
            **firewall_result,
            "adapter": adapter_name,
            "enabled": enabled,
        }

    state = "enabled" if enabled else "disabled"
    result = _run_netsh(
        "interface",
        "set",
        "interface",
        f"name={adapter_name}",
        f"admin={state}",
    )

    ok = result.returncode == 0
    if ok:
        message = f"{adapter_name} {state}."
    elif not is_admin():
        message = f"Could not set {adapter_name}. Run as Administrator."
    else:
        detail = (result.stderr or result.stdout or "").strip()
        message = detail or f"Could not set {adapter_name}."

    return {
        "ok": ok,
        "message": message,
        "adapter": adapter_name,
        "enabled": enabled,
        "returncode": result.returncode,
    }
