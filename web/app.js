let currentStatus = null;
let statusTimer = null;
let currentLanguage = localStorage.getItem("laxyControlLanguage") || "th";
let appOptions = [];
let appSourceFilter = "all";

const el = (id) => document.getElementById(id);
const hotkeyOptions = [
  "f6",
  "f7",
  "f8",
  "f9",
  "f10",
  "f11",
  "f12",
  "ctrl+f6",
  "ctrl+f7",
  "ctrl+f8",
  "ctrl+f9",
  "ctrl+f10",
  "alt+f6",
  "alt+f7",
  "alt+f8",
  "alt+f9",
  "alt+f10",
  "shift+f6",
  "shift+f7",
  "shift+f8",
  "shift+f9",
  "shift+f10",
  "ctrl+alt+f6",
  "ctrl+alt+f7",
  "ctrl+alt+f8",
  "ctrl+alt+f9",
  "ctrl+alt+f10",
  "ctrl+shift+f8",
  "alt+shift+f8",
  "space",
  "ctrl+space",
  "alt+space",
];

const translations = {
  en: {
    subtitle: "Local network control",
    language: "Language",
    checking: "Checking...",
    service: "Service",
    networkState: "Network",
    hotkey: "Hotkey",
    adapter: "Adapter",
    testControls: "Controls",
    testControlsHelp: "Pause automatically restores after the time below.",
    testPause: "Pause",
    testRestore: "Restore",
    testToggle: "Toggle",
    showOverlay: "Overlay",
    closeOverlay: "Hide",
    exitService: "Exit",
    waitingStatus: "Waiting for status...",
    settings: "Settings",
    settingsHelp: "Saved changes apply immediately.",
    globalHotkey: "Global Hotkey",
    mode: "Mode",
    modeToggle: "Toggle",
    modeHold: "Hold",
    networkAdapter: "Network Adapter",
    customAdapter: "Custom Adapter Name",
    customAdapterPlaceholder: "Optional, if not listed",
    blockScope: "Block Target",
    blockScopeAll: "All network",
    blockScopeApp: "Selected app",
    adapterCutWarning: "All-network mode disables the selected adapter. Your own connection will drop briefly.",
    appSelect: "Running App",
    refreshApps: "Refresh Apps",
    appPath: "App .exe Path",
    appPathPlaceholder: "Select a running app or paste an .exe path",
    appSearchPlaceholder: "Search app name, window title, exe, or path",
    appFirewallUnavailable: "Per-app blocking is unavailable because Windows policy disables local firewall rules.",
    appFilterAll: "All",
    appFilterRunning: "Running",
    appFilterShortcuts: "Shortcuts",
    appFilterInstalled: "Installed",
    noApps: "No apps found. Try another search or paste the .exe path below.",
    restoreDelay: "Auto restore",
    seconds: "sec",
    openUiOnStart: "Open Web UI on startup",
    showNotifications: "Show toast notifications",
    overlayStartup: "Enable mini overlay",
    saveSettings: "Save",
    refreshAdapter: "Refresh",
    running: "Running",
    stopped: "Stopped",
    paused: "Paused",
    readyState: "Ready",
    modeToggleShort: "toggle",
    modeHoldShort: "hold",
    administrator: "Administrator",
    notAdministrator: "Not Administrator",
    notSelected: "Not selected",
    noAdapters: "No adapters found",
    saved: "saved",
    ready: "Ready.",
    settingsSaved: "Settings saved.",
    confirmPause: "Pause network access now?",
    confirmRestore: "Restore network access now?",
    confirmToggle: "Toggle network state now?",
    confirmShutdown: "Exit LaxyControl now?",
  },
  th: {
    subtitle: "ควบคุมเครือข่ายในเครื่อง",
    language: "ภาษา",
    checking: "กำลังตรวจสอบ...",
    service: "บริการ",
    networkState: "เครือข่าย",
    hotkey: "ปุ่มลัด",
    adapter: "อะแดปเตอร์",
    testControls: "ควบคุม",
    testControlsHelp: "เมื่อพักเครือข่าย ระบบจะคืนค่าอัตโนมัติตามเวลาที่ตั้งไว้",
    testPause: "พัก",
    testRestore: "คืนค่า",
    testToggle: "สลับ",
    showOverlay: "Overlay",
    closeOverlay: "ซ่อน",
    exitService: "ออก",
    waitingStatus: "กำลังรอสถานะ...",
    settings: "ตั้งค่า",
    settingsHelp: "บันทึกแล้วมีผลทันที",
    globalHotkey: "ปุ่มลัดหลัก",
    mode: "โหมด",
    modeToggle: "สลับ",
    modeHold: "กดค้าง",
    networkAdapter: "อะแดปเตอร์เครือข่าย",
    customAdapter: "ชื่ออะแดปเตอร์เอง",
    customAdapterPlaceholder: "ใส่เองถ้าไม่มีในรายการ",
    blockScope: "เป้าหมายที่ตัด",
    blockScopeAll: "ตัดทั้งเครื่อง",
    blockScopeApp: "ตัดเฉพาะแอพ",
    adapterCutWarning: "โหมดตัดทั้งเครื่องจะปิด adapter ที่เลือก เครื่องคุณจะหลุดเน็ตชั่วคราว",
    appSelect: "แอพที่กำลังรัน",
    refreshApps: "รีเฟรชแอพ",
    appPath: "Path ไฟล์ .exe",
    appPathPlaceholder: "เลือกแอพที่รันอยู่ หรือวาง path .exe",
    appSearchPlaceholder: "ค้นหาจากชื่อแอพหรือ path",
    appFirewallUnavailable: "ตัดเฉพาะแอพใช้งานไม่ได้ เพราะ Windows policy ปิด local firewall rules",
    noApps: "ไม่พบแอพที่มี path",
    restoreDelay: "คืนค่าอัตโนมัติ",
    seconds: "วินาที",
    openUiOnStart: "เปิด Web UI ตอนเริ่มโปรแกรม",
    showNotifications: "แสดง toast notification",
    overlayStartup: "เปิด mini overlay",
    saveSettings: "บันทึก",
    refreshAdapter: "รีเฟรช",
    running: "ทำงาน",
    stopped: "หยุด",
    paused: "พักอยู่",
    readyState: "พร้อม",
    modeToggleShort: "สลับ",
    modeHoldShort: "กดค้าง",
    administrator: "Administrator",
    notAdministrator: "ไม่ใช่ Administrator",
    notSelected: "ยังไม่ได้เลือก",
    noAdapters: "ไม่พบอะแดปเตอร์",
    saved: "บันทึกไว้",
    ready: "พร้อมใช้งาน",
    settingsSaved: "บันทึกการตั้งค่าแล้ว",
    confirmPause: "พักการเชื่อมต่อเครือข่ายตอนนี้?",
    confirmRestore: "คืนค่าการเชื่อมต่อเครือข่ายตอนนี้?",
    confirmToggle: "สลับสถานะเครือข่ายตอนนี้?",
    confirmShutdown: "ออกจาก LaxyControl ตอนนี้?",
  },
};

function t(key) {
  const language = translations[currentLanguage] ? currentLanguage : "th";
  return translations[language][key] || translations.en[key] || key;
}

function modeLabel(mode) {
  return mode === "hold" ? t("modeHoldShort") : t("modeToggleShort");
}

function restoreDelayValue() {
  const value = Number.parseFloat(el("restoreDelayQuick").value || el("restoreDelay").value || "3");
  if (!Number.isFinite(value)) {
    return 3;
  }
  return Math.min(60, Math.max(1.5, value));
}

function syncRestoreInputs(value) {
  const rounded = Number.parseFloat(value || 3).toFixed(1).replace(/\.0$/, "");
  el("restoreDelay").value = rounded;
  el("restoreDelayQuick").value = rounded;
}

function applyLanguage() {
  document.documentElement.lang = currentLanguage;
  el("language").value = currentLanguage;

  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });

  if (currentStatus) {
    renderStatus(currentStatus);
    fillSettings(currentStatus);
  }
}

function fillHotkeyOptions() {
  const list = el("hotkeyOptions");
  list.innerHTML = "";
  hotkeyOptions.forEach((hotkey) => {
    const option = document.createElement("option");
    option.value = hotkey;
    list.append(option);
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "Request failed");
  }
  return data;
}

function setResult(result) {
  const target = el("lastResult");
  target.textContent = result.message || JSON.stringify(result);
  target.className = `result ${result.ok ? "ok" : "bad"}`;
}

function fillSettings(status) {
  const settings = status.settings;
  el("hotkey").value = settings.hotkey || "f8";
  el("mode").value = settings.mode || "toggle";
  el("blockScope").value = settings.block_scope || "all";
  el("appPath").value = settings.app_path || "";
  el("openUiOnStart").checked = Boolean(settings.open_ui_on_start);
  el("showNotifications").checked = Boolean(settings.show_notifications);
  el("overlayEnabled").checked = Boolean(settings.overlay_enabled);
  syncRestoreInputs(settings.restore_delay_seconds || status.max_pause_seconds || 3);
  updateTargetFields();
  fillApps(settings.app_path || "");

  const adapterSelect = el("adapter");
  const selected = settings.adapter || "";
  adapterSelect.innerHTML = "";

  if (!status.adapters.length) {
    adapterSelect.append(new Option(t("noAdapters"), ""));
  }

  for (const row of status.adapters) {
    adapterSelect.append(new Option(`${row.name} (${row.admin_state}/${row.state})`, row.name));
  }

  if (selected && !Array.from(adapterSelect.options).some((option) => option.value === selected)) {
    adapterSelect.prepend(new Option(`${selected} (${t("saved")})`, selected));
  }

  adapterSelect.value = selected;
}

function renderStatus(status) {
  currentStatus = status;
  el("serviceState").textContent = status.service_running ? t("running") : t("stopped");
  const networkPaused = Boolean(status.network_paused);
  el("networkStateValue").textContent = networkPaused ? t("paused") : t("readyState");
  el("networkStateValue").className = networkPaused ? "bad" : "ok";
  el("hotkeyState").textContent = `${status.settings.hotkey} (${modeLabel(status.settings.mode)})`;

  if (status.settings.block_scope === "app") {
    el("adapterState").textContent = status.selected_app_path || t("notSelected");
  } else {
    const adapterStatus = status.selected_adapter_status;
    el("adapterState").textContent = adapterStatus
      ? `${adapterStatus.name}: ${adapterStatus.admin_state}/${adapterStatus.state}`
      : status.settings.adapter || t("notSelected");
  }

  el("adminStatus").textContent = status.is_admin ? t("administrator") : t("notAdministrator");
  el("adminStatus").className = status.is_admin ? "ok" : "bad";

  setResult(status.last_result || { ok: true, message: t("ready") });
}

async function refreshStatus(fillForm = false) {
  const status = await api("/api/status");
  renderStatus(status);
  if (fillForm) {
    fillSettings(status);
  }
}

function collectSettingsPayload() {
  const customAdapter = el("customAdapter").value.trim();
  return {
    hotkey: el("hotkey").value.trim(),
    mode: el("mode").value,
    adapter: customAdapter || el("adapter").value,
    block_scope: el("blockScope").value,
    app_path: el("appPath").value.trim(),
    open_ui_on_start: el("openUiOnStart").checked,
    show_notifications: el("showNotifications").checked,
    overlay_enabled: el("overlayEnabled").checked,
    restore_delay_seconds: restoreDelayValue(),
  };
}

function updateTargetFields() {
  const appMode = el("blockScope").value === "app";
  const appUnavailable = appMode && currentStatus && !currentStatus.local_firewall_rules_allowed;
  document.querySelectorAll(".app-target").forEach((node) => {
    node.hidden = !appMode;
  });
  el("adapterCutWarning").hidden = appMode;
  el("appFirewallWarning").hidden = !appUnavailable;
}

function fillApps(selectedPath = "") {
  const appList = el("appList");
  const query = el("appSearch").value.trim().toLowerCase();
  const visibleApps = appOptions
    .filter((app) => appSourceFilter === "all" || (app.source || "").includes(appSourceFilter))
    .filter((app) => !query || (app.search || `${app.name} ${app.path}`).toLowerCase().includes(query))
    .slice(0, 120);
  appList.innerHTML = "";

  if (!visibleApps.length) {
    const empty = document.createElement("p");
    empty.className = "app-empty";
    empty.textContent = t("noApps");
    appList.append(empty);
    return;
  }

  for (const app of visibleApps) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `app-option ${app.path.toLowerCase() === selectedPath.toLowerCase() ? "selected" : ""}`;
    button.dataset.path = app.path;
    button.title = app.path;

    const icon = document.createElement("span");
    icon.className = "app-icon";
    const image = document.createElement("img");
    image.alt = "";
    image.loading = "lazy";
    image.src = `/api/app-icon?path=${encodeURIComponent(app.path)}`;
    image.addEventListener("error", () => {
      image.remove();
      icon.textContent = (app.name || "?").slice(0, 1).toUpperCase();
    });
    icon.append(image);

    const text = document.createElement("span");
    text.className = "app-text";
    const name = document.createElement("strong");
    name.textContent = app.name;
    const meta = document.createElement("em");
    meta.textContent = [
      app.window_title && app.window_title !== app.name ? app.window_title : "",
      app.source || "",
    ].filter(Boolean).join(" - ");
    const path = document.createElement("small");
    path.textContent = app.path;
    text.append(name);
    if (meta.textContent) {
      text.append(meta);
    }
    text.append(path);

    button.append(icon, text);
    appList.append(button);
  }
}

async function refreshApps(selectedPath = el("appPath").value.trim()) {
  const result = await api("/api/apps");
  appOptions = result.apps || [];
  fillApps(selectedPath);
}

async function saveSettings(silent = false) {
  const result = await api("/api/settings", {
    method: "POST",
    body: JSON.stringify(collectSettingsPayload()),
  });
  if (currentStatus) {
    currentStatus.settings = result.settings;
  }
  syncRestoreInputs(result.settings.restore_delay_seconds);
  if (!silent) {
    setResult({ ok: true, message: t("settingsSaved") });
  }
  return result.settings;
}

async function persistQuickRestoreDelay() {
  if (!currentStatus) {
    return;
  }

  const current = Number.parseFloat(currentStatus.settings.restore_delay_seconds || currentStatus.max_pause_seconds || 3);
  const next = restoreDelayValue();
  syncRestoreInputs(next);
  if (Math.abs(current - next) > 0.001) {
    await saveSettings(true);
  }
}

async function runAction(action) {
  const confirmations = {
    pause: "confirmPause",
    restore: "confirmRestore",
    toggle: "confirmToggle",
    shutdown: "confirmShutdown",
  };
  const confirmationKey = confirmations[action];
  if (confirmationKey && !window.confirm(t(confirmationKey))) {
    return;
  }

  try {
    if (action === "pause" || action === "toggle") {
      await persistQuickRestoreDelay();
    }
    const result = await api("/api/action", {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    setResult(result);
    if (action === "shutdown") {
      closeWebUi();
      return;
    }
  } catch (error) {
    setResult({ ok: false, message: error.message });
  }
  await refreshStatus(false);
}

function closeWebUi() {
  if (statusTimer) {
    clearInterval(statusTimer);
  }

  document.body.innerHTML = "";
  window.open("", "_self");
  window.close();
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action));
});

el("language").addEventListener("change", (event) => {
  currentLanguage = event.target.value;
  localStorage.setItem("laxyControlLanguage", currentLanguage);
  applyLanguage();
});

el("restoreDelayQuick").addEventListener("input", () => {
  el("restoreDelay").value = el("restoreDelayQuick").value;
});

el("restoreDelay").addEventListener("input", () => {
  el("restoreDelayQuick").value = el("restoreDelay").value;
});

el("blockScope").addEventListener("change", updateTargetFields);

el("appSearch").addEventListener("input", () => {
  fillApps(el("appPath").value.trim());
});

el("appFilters").addEventListener("click", (event) => {
  const button = event.target.closest("[data-source-filter]");
  if (!button) {
    return;
  }

  appSourceFilter = button.dataset.sourceFilter || "all";
  el("appFilters").querySelectorAll("[data-source-filter]").forEach((node) => {
    node.classList.toggle("selected", node === button);
  });
  fillApps(el("appPath").value.trim());
});

el("appList").addEventListener("click", (event) => {
  const option = event.target.closest(".app-option");
  if (!option) {
    return;
  }
  el("appPath").value = option.dataset.path || "";
  fillApps(el("appPath").value.trim());
});

el("restoreDelayQuick").addEventListener("change", () => {
  syncRestoreInputs(restoreDelayValue());
  saveSettings(true).catch((error) => setResult({ ok: false, message: error.message }));
});

el("refreshButton").addEventListener("click", () => refreshStatus(true));
el("refreshAppsButton").addEventListener("click", () => {
  refreshApps().catch((error) => setResult({ ok: false, message: error.message }));
});

el("settingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await saveSettings(false);
  } catch (error) {
    setResult({ ok: false, message: error.message });
  }

  await refreshStatus(true);
});

fillHotkeyOptions();
applyLanguage();
refreshApps().catch(() => undefined).finally(() => refreshStatus(true));
statusTimer = setInterval(() => refreshStatus(false), 1500);
