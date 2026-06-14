import ctypes
import subprocess


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FIREWALL_GROUP = "LaxyControl Rules"
FIREWALL_OUT_RULE = "LaxyControl Pause Outbound"
FIREWALL_IN_RULE = "LaxyControl Pause Inbound"
FIREWALL_READY = False


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


def _firewall_rule_exists(rule_name):
    result = _run_netsh("advfirewall", "firewall", "show", "rule", f"name={rule_name}")
    return result.returncode == 0 and rule_name.lower() in result.stdout.lower()


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
        f"group={FIREWALL_GROUP}",
        "profile=any",
        "program=any",
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


def prepare_fast_mode():
    return _ensure_firewall_rules().returncode == 0


def set_firewall_paused(paused):
    ensure = _ensure_firewall_rules()
    if ensure.returncode != 0:
        return {
            "ok": False,
            "message": (ensure.stderr or ensure.stdout or "Could not prepare firewall rules.").strip(),
            "returncode": ensure.returncode,
        }

    enabled = "yes" if paused else "no"
    group_result = _run_netsh(
        "advfirewall",
        "firewall",
        "set",
        "rule",
        f"group={FIREWALL_GROUP}",
        "new",
        f"enable={enabled}",
    )
    if group_result.returncode == 0:
        results = [group_result]
    else:
        results = [
            _run_netsh(
                "advfirewall",
                "firewall",
                "set",
                "rule",
                f"name={rule_name}",
                "new",
                f"enable={enabled}",
            )
            for rule_name in (FIREWALL_OUT_RULE, FIREWALL_IN_RULE)
        ]

    failed = next((result for result in results if result.returncode != 0), None)
    if failed:
        return {
            "ok": False,
            "message": (failed.stderr or failed.stdout or "Could not update firewall rules.").strip(),
            "returncode": failed.returncode,
        }

    action = "paused" if paused else "restored"
    return {
        "ok": True,
        "message": f"Network access {action} with local firewall rules.",
        "returncode": 0,
        "method": "firewall",
    }


def _set_firewall_rules_enabled(rule_names, enabled):
    ensure = _ensure_firewall_rules()
    if ensure.returncode != 0:
        return {
            "ok": False,
            "message": (ensure.stderr or ensure.stdout or "Could not prepare firewall rules.").strip(),
            "returncode": ensure.returncode,
        }

    enabled_value = "yes" if enabled else "no"
    results = [
        _run_netsh(
            "advfirewall",
            "firewall",
            "set",
            "rule",
            f"name={rule_name}",
            "new",
            f"enable={enabled_value}",
        )
        for rule_name in rule_names
    ]

    failed = next((result for result in results if result.returncode != 0), None)
    if failed:
        return {
            "ok": False,
            "message": (failed.stderr or failed.stdout or "Could not update firewall rules.").strip(),
            "returncode": failed.returncode,
        }

    return {"ok": True, "returncode": 0}


def set_soft_lag_paused(paused):
    if paused:
        outbound_result = _set_firewall_rules_enabled((FIREWALL_OUT_RULE,), False)
        if not outbound_result["ok"]:
            return outbound_result

        inbound_result = _set_firewall_rules_enabled((FIREWALL_IN_RULE,), True)
        if not inbound_result["ok"]:
            return inbound_result

        return {
            "ok": True,
            "message": "Soft lag enabled with inbound firewall rule.",
            "returncode": 0,
            "method": "soft_lag",
        }

    restore_result = _set_firewall_rules_enabled((FIREWALL_IN_RULE, FIREWALL_OUT_RULE), False)
    if not restore_result["ok"]:
        return restore_result

    return {
        "ok": True,
        "message": "Soft lag restored.",
        "returncode": 0,
        "method": "soft_lag",
    }


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


def set_adapter_state(adapter_name, enabled):
    if not adapter_name:
        return {
            "ok": False,
            "message": "No adapter selected.",
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
        return {
            "ok": True,
            "message": f"{adapter_name} {state}.",
            "adapter": adapter_name,
            "enabled": enabled,
            "returncode": result.returncode,
            "method": "adapter",
        }

    firewall_result = set_firewall_paused(not enabled)
    if firewall_result["ok"]:
        return {
            **firewall_result,
            "adapter": adapter_name,
            "enabled": enabled,
        }

    if not is_admin():
        message = f"Could not set {adapter_name}. Run as Administrator."
    else:
        adapter_detail = (result.stderr or result.stdout or "").strip()
        firewall_detail = firewall_result.get("message", "")
        message = adapter_detail or firewall_detail or f"Could not set {adapter_name}."

    return {
        "ok": False,
        "message": message,
        "adapter": adapter_name,
        "enabled": enabled,
        "returncode": result.returncode,
    }
