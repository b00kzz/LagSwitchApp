import json

from core.paths import app_dir

CONFIG_FILE = app_dir() / "config.json"

DEFAULT_SETTINGS = {
    "hotkey": "f8",
    "mode": "hold",
    "adapter": "",
    "open_ui_on_start": True,
    "show_notifications": True,
    "overlay_enabled": False,
    "overlay_x": 40,
    "overlay_y": 40,
}


def normalize_settings(settings):
    normalized = dict(DEFAULT_SETTINGS)
    normalized.update(settings or {})

    normalized["hotkey"] = str(normalized.get("hotkey") or "f8").strip().lower()
    mode = str(normalized.get("mode") or "hold").strip().lower()
    normalized["mode"] = "hold" if mode in ("hold", "2") else "toggle"
    normalized["adapter"] = str(normalized.get("adapter") or "").strip()
    normalized["open_ui_on_start"] = bool(normalized.get("open_ui_on_start"))
    normalized["show_notifications"] = bool(normalized.get("show_notifications"))
    normalized["overlay_enabled"] = bool(normalized.get("overlay_enabled"))
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
