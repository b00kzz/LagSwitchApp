let currentStatus = null;
let statusTimer = null;
let currentLanguage = localStorage.getItem("laxyControlLanguage") || "th";

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

const networkPresets = {
  stable: { delay: 40, jitter: 10, loss: 0 },
  busy: { delay: 120, jitter: 45, loss: 2 },
  mobile: { delay: 180, jitter: 90, loss: 4 },
  lossy: { delay: 260, jitter: 120, loss: 8 },
};

const translations = {
  en: {
    subtitle: "Local network simulator for QA and connection testing",
    language: "Language",
    checking: "Checking...",
    service: "Service",
    networkState: "Lag",
    hotkey: "Hotkey",
    adapter: "Profile",
    testControls: "Controls",
    testControlsHelp: "Lag automatically stops after the time below.",
    testPause: "Start Lag",
    testRestore: "Stop Lag",
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
    networkAdapter: "Network Adapter (not changed)",
    customAdapter: "Custom Adapter Name",
    customAdapterPlaceholder: "Optional; kept for old configs",
    blockScope: "Lag Target",
    blockScopeAll: "All packets",
    adapterCutWarning: "Lag mode adds delay and packet loss without disabling the adapter.",
    presets: "Network presets",
    presetStable: "Stable Wi-Fi",
    presetBusy: "Busy Wi-Fi",
    presetMobile: "Mobile Data",
    presetLossy: "Packet Loss",
    diagnostics: "Diagnostics",
    diagnosticsHelp: "Run before and during lag to compare the real connection.",
    diagnosticTarget: "Ping target",
    runDiagnostics: "Run",
    diagnosticAvg: "Average",
    diagnosticJitter: "Jitter",
    diagnosticLoss: "Loss",
    diagnosticsWaiting: "No diagnostic run yet.",
    diagnosticsRunning: "Running diagnostic...",
    diagnosticsComplete: "Diagnostic complete.",
    restoreDelay: "Auto restore",
    lagDelay: "Delay",
    lagJitter: "Jitter",
    packetLoss: "Packet loss",
    milliseconds: "ms",
    seconds: "sec",
    openUiOnStart: "Open Web UI on startup",
    showNotifications: "Show toast notifications",
    overlayStartup: "Enable mini overlay",
    saveSettings: "Save",
    refreshAdapter: "Refresh",
    running: "Running",
    stopped: "Stopped",
    paused: "Lagging",
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
    confirmPause: "Start lag now?",
    confirmRestore: "Stop lag now?",
    confirmToggle: "Toggle lag state now?",
    confirmShutdown: "Exit LaxyControl now?",
  },
  th: {
    subtitle: "จำลองสภาพเครือข่ายในเครื่องสำหรับ QA และทดสอบการเชื่อมต่อ",
    language: "ภาษา",
    checking: "กำลังตรวจสอบ...",
    service: "บริการ",
    networkState: "Lag",
    hotkey: "ปุ่มลัด",
    adapter: "โปรไฟล์",
    testControls: "ควบคุม",
    testControlsHelp: "เมื่อเริ่ม lag ระบบจะหยุดอัตโนมัติตามเวลาที่ตั้งไว้",
    testPause: "เริ่ม Lag",
    testRestore: "หยุด Lag",
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
    networkAdapter: "อะแดปเตอร์เครือข่าย (ไม่ถูกปิด)",
    customAdapter: "ชื่ออะแดปเตอร์เอง",
    customAdapterPlaceholder: "ใส่เองถ้าไม่มีในรายการ",
    blockScope: "เป้าหมาย Lag",
    blockScopeAll: "ทุก packet",
    adapterCutWarning: "โหมด Lag จะเพิ่ม delay และ packet loss โดยไม่ปิด adapter",
    presets: "โปรไฟล์เครือข่าย",
    presetStable: "Wi-Fi เสถียร",
    presetBusy: "Wi-Fi หนาแน่น",
    presetMobile: "เน็ตมือถือ",
    presetLossy: "Packet loss สูง",
    diagnostics: "ตรวจสภาพเน็ต",
    diagnosticsHelp: "รันก่อนและระหว่างเปิด lag เพื่อเทียบค่าจริงของการเชื่อมต่อ",
    diagnosticTarget: "เป้าหมาย ping",
    runDiagnostics: "รัน",
    diagnosticAvg: "ค่าเฉลี่ย",
    diagnosticJitter: "Jitter",
    diagnosticLoss: "Loss",
    diagnosticsWaiting: "ยังไม่ได้รันการตรวจสภาพเน็ต",
    diagnosticsRunning: "กำลังตรวจสภาพเน็ต...",
    diagnosticsComplete: "ตรวจสภาพเน็ตเสร็จแล้ว",
    restoreDelay: "หยุดอัตโนมัติ",
    lagDelay: "Delay",
    lagJitter: "Jitter",
    packetLoss: "Packet loss",
    milliseconds: "ms",
    seconds: "วินาที",
    openUiOnStart: "เปิด Web UI ตอนเริ่มโปรแกรม",
    showNotifications: "แสดง toast notification",
    overlayStartup: "เปิด mini overlay",
    saveSettings: "บันทึก",
    refreshAdapter: "รีเฟรช",
    running: "ทำงาน",
    stopped: "หยุด",
    paused: "กำลัง Lag",
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
    confirmPause: "เริ่มทำให้ lag ตอนนี้?",
    confirmRestore: "หยุด lag ตอนนี้?",
    confirmToggle: "สลับสถานะ lag ตอนนี้?",
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

function numberValue(id, fallback, min, max) {
  const value = Number.parseFloat(el(id).value || `${fallback}`);
  if (!Number.isFinite(value)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, value));
}

function syncRestoreInputs(value) {
  const rounded = Number.parseFloat(value || 3).toFixed(1).replace(/\.0$/, "");
  el("restoreDelay").value = rounded;
  el("restoreDelayQuick").value = rounded;
}

function syncLagInputs(settings = {}) {
  el("lagDelay").value = Math.round(Number(settings.lag_delay_ms ?? 120));
  el("lagJitter").value = Math.round(Number(settings.lag_jitter_ms ?? 30));
  el("lagLoss").value = Number(settings.lag_loss_percent ?? 4).toFixed(1).replace(/\.0$/, "");
}

function applyPreset(name) {
  const preset = networkPresets[name];
  if (!preset) {
    return;
  }

  el("lagDelay").value = preset.delay;
  el("lagJitter").value = preset.jitter;
  el("lagLoss").value = preset.loss;
  setResult({
    ok: true,
    message: `${t("presets")}: ${t(`preset${name.charAt(0).toUpperCase()}${name.slice(1)}`)}`,
  });
  saveSettings(true).catch((error) => setResult({ ok: false, message: error.message }));
}

function setDiagnosticResult(result) {
  el("diagAverage").textContent = result.average_ms == null ? "-" : `${result.average_ms}ms`;
  el("diagJitter").textContent = result.jitter_ms == null ? "-" : `${result.jitter_ms}ms`;
  el("diagLoss").textContent = result.loss_percent == null ? "-" : `${result.loss_percent}%`;

  const samples = Array.isArray(result.samples_ms) && result.samples_ms.length
    ? ` (${result.samples_ms.join(", ")}ms)`
    : "";
  const message = result.message || t("diagnosticsComplete");
  el("diagnosticResult").textContent = `${message}${samples}`;
  el("diagnosticResult").className = `result ${result.ok ? "ok" : "bad"}`;
}

async function runDiagnostics() {
  const target = el("diagnosticTarget").value.trim() || "1.1.1.1";
  el("diagnosticResult").textContent = t("diagnosticsRunning");
  el("diagnosticResult").className = "result";

  try {
    const result = await api(`/api/diagnostics?target=${encodeURIComponent(target)}`);
    setDiagnosticResult(result);
  } catch (error) {
    setDiagnosticResult({ ok: false, message: error.message });
  }
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
  el("hotkey").value = settings.hotkey || "g";
  el("mode").value = settings.mode || "toggle";
  el("blockScope").value = settings.block_scope || "all";
  el("openUiOnStart").checked = Boolean(settings.open_ui_on_start);
  el("showNotifications").checked = Boolean(settings.show_notifications);
  el("overlayEnabled").checked = Boolean(settings.overlay_enabled);
  syncRestoreInputs(settings.restore_delay_seconds || status.max_pause_seconds || 3);
  syncLagInputs(settings);

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

  const profile = status.active_lag_profile && Object.keys(status.active_lag_profile).length
    ? status.active_lag_profile
    : {
        delay_ms: status.settings.lag_delay_ms,
        jitter_ms: status.settings.lag_jitter_ms,
        loss_percent: status.settings.lag_loss_percent,
      };
  el("adapterState").textContent = `${profile.delay_ms || 0}ms / ${profile.jitter_ms || 0}ms / ${profile.loss_percent || 0}%`;

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
  return {
    hotkey: el("hotkey").value.trim(),
    mode: el("mode").value,
    adapter: "",
    block_scope: el("blockScope").value,
    app_path: "",
    lag_delay_ms: numberValue("lagDelay", 120, 0, 5000),
    lag_jitter_ms: numberValue("lagJitter", 30, 0, 5000),
    lag_loss_percent: numberValue("lagLoss", 4, 0, 100),
    lag_filter: "ip",
    open_ui_on_start: el("openUiOnStart").checked,
    show_notifications: el("showNotifications").checked,
    overlay_enabled: el("overlayEnabled").checked,
    restore_delay_seconds: restoreDelayValue(),
  };
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
    const payload = { action };
    if (action === "pause" || action === "toggle") {
      syncRestoreInputs(restoreDelayValue());
      payload.settings = collectSettingsPayload();
    }
    const result = await api("/api/action", {
      method: "POST",
      body: JSON.stringify(payload),
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

document.querySelectorAll("[data-preset]").forEach((button) => {
  button.addEventListener("click", () => applyPreset(button.dataset.preset));
});

el("runDiagnostics").addEventListener("click", runDiagnostics);

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

el("restoreDelayQuick").addEventListener("change", () => {
  syncRestoreInputs(restoreDelayValue());
  saveSettings(true).catch((error) => setResult({ ok: false, message: error.message }));
});

el("refreshButton").addEventListener("click", () => refreshStatus(true));

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
refreshStatus(true);
statusTimer = setInterval(() => refreshStatus(false), 1500);
