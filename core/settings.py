import json

from core.paths import app_dir

CONFIG_FILE = app_dir() / "config.json"

DEFAULT_SETTINGS = {
    "hotkey": "g",
    "mode": "toggle",
    "adapter": "",
    "block_scope": "all",
    "app_path": "",
    "lag_delay_ms": 120,
    "lag_jitter_ms": 30,
    "lag_loss_percent": 4.0,
    "lag_filter": "ip",
    "open_ui_on_start": True,
    "show_notifications": True,
    "overlay_enabled": False,
    "overlay_x": 40,
    "overlay_y": 40,
    "restore_delay_seconds": 3.0,
    "secure_browser_enabled": True,
    "secure_browser_allowed_hosts": ["127.0.0.1", "localhost"],
}


def normalize_settings(settings):
    normalized = dict(DEFAULT_SETTINGS)
    normalized.update(settings or {})

    normalized["hotkey"] = str(normalized.get("hotkey") or DEFAULT_SETTINGS["hotkey"]).strip().lower()
    mode = str(normalized.get("mode") or DEFAULT_SETTINGS["mode"]).strip().lower()
    normalized["mode"] = "hold" if mode in ("hold", "2") else "toggle"
    normalized["adapter"] = str(normalized.get("adapter") or "").strip()
    block_scope = str(normalized.get("block_scope") or "all").strip().lower()
    normalized["block_scope"] = "app" if block_scope in ("app", "per-app", "program") else "all"
    normalized["app_path"] = str(normalized.get("app_path") or "").strip().strip('"')
    normalized["lag_filter"] = str(normalized.get("lag_filter") or DEFAULT_SETTINGS["lag_filter"]).strip() or DEFAULT_SETTINGS["lag_filter"]
    normalized["open_ui_on_start"] = bool(normalized.get("open_ui_on_start"))
    normalized["show_notifications"] = bool(normalized.get("show_notifications"))
    normalized["overlay_enabled"] = bool(normalized.get("overlay_enabled"))
    normalized["secure_browser_enabled"] = bool(normalized.get("secure_browser_enabled"))
    try:
        restore_delay = float(normalized.get("restore_delay_seconds", DEFAULT_SETTINGS["restore_delay_seconds"]))
    except (TypeError, ValueError):
        restore_delay = DEFAULT_SETTINGS["restore_delay_seconds"]
    normalized["restore_delay_seconds"] = min(60.0, max(1.5, restore_delay))

    for key, default, minimum, maximum in (
        ("lag_delay_ms", DEFAULT_SETTINGS["lag_delay_ms"], 0, 5000),
        ("lag_jitter_ms", DEFAULT_SETTINGS["lag_jitter_ms"], 0, 5000),
        ("lag_loss_percent", DEFAULT_SETTINGS["lag_loss_percent"], 0.0, 100.0),
    ):
        try:
            value = float(normalized.get(key, default))
        except (TypeError, ValueError):
            value = default
        value = min(maximum, max(minimum, value))
        normalized[key] = int(value) if key.endswith("_ms") else value

    allowed_hosts = normalized.get("secure_browser_allowed_hosts")
    if not isinstance(allowed_hosts, list):
        allowed_hosts = DEFAULT_SETTINGS["secure_browser_allowed_hosts"]
    normalized["secure_browser_allowed_hosts"] = [
        str(host).strip().lower()
        for host in allowed_hosts
        if str(host or "").strip()
    ]
    normalized.pop("exit_hotkey", None)

    for key in ("overlay_x", "overlay_y"):
        try:
            normalized[key] = int(normalized.get(key, DEFAULT_SETTINGS[key]))
        except (TypeError, ValueError):
            normalized[key] = DEFAULT_SETTINGS[key]

    return normalized


def load_settings():
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_SETTINGS)

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)

    return normalize_settings(data)


def save_settings(settings):
    normalized = normalize_settings(settings)
    CONFIG_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return normalized
