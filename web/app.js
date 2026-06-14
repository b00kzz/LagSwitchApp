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
const translations = {
  en: {
    subtitle: "Local network control service with a web test dashboard.",
    language: "Language",
    checking: "Checking...",
    service: "Service",
    networkState: "Network",
    hotkey: "Hotkey",
    adapter: "Adapter",
    testControls: "Test Controls",
    testControlsHelp: "These buttons use the selected adapter. Run as Administrator for real pause/restore actions.",
    testPause: "Test Pause",
    testRestore: "Test Restore",
    testToggle: "Test Toggle",
    showOverlay: "Show Overlay",
    closeOverlay: "Close Overlay",
    exitService: "Exit Service",
    waitingStatus: "Waiting for status...",
    settings: "Settings",
    settingsHelp: "Saved changes apply to the global hotkey immediately.",
    globalHotkey: "Global Hotkey",
    mode: "Mode",
    modeToggle: "Toggle: press once to pause, press again to restore",
    modeHold: "Hold: hold to pause, release to restore",
    networkAdapter: "Network Adapter",
    customAdapter: "Custom Adapter Name",
    customAdapterPlaceholder: "Optional, if not listed",
    openUiOnStart: "Open Web UI on startup",
    showNotifications: "Show toast notifications",
    overlayStartup: "Enable mini overlay on startup",
    saveSettings: "Save Settings",
    refreshAdapter: "Refresh Adapter",
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
    subtitle: "บริการควบคุมเครือข่ายในเครื่อง พร้อมหน้าเว็บสำหรับทดสอบและตั้งค่า",
    language: "ภาษา",
    checking: "กำลังตรวจสอบ...",
    service: "บริการ",
    networkState: "เครือข่าย",
    hotkey: "ปุ่มลัด",
    adapter: "อะแดปเตอร์",
    testControls: "ปุ่มทดสอบ",
    testControlsHelp: "ปุ่มเหล่านี้ใช้อะแดปเตอร์ที่เลือกไว้ ต้องรันแบบ Administrator เพื่อพัก/คืนค่าเครือข่ายจริง",
    testPause: "ทดสอบพัก",
    testRestore: "ทดสอบคืนค่า",
    testToggle: "ทดสอบสลับ",
    showOverlay: "แสดง Overlay",
    closeOverlay: "ปิด Overlay",
    exitService: "ออกจากโปรแกรม",
    waitingStatus: "กำลังรอสถานะ...",
    settings: "ตั้งค่า",
    settingsHelp: "บันทึกแล้วจะมีผลกับปุ่มลัดทันที",
    globalHotkey: "ปุ่มลัดหลัก",
    mode: "โหมด",
    modeToggle: "สลับ: กดหนึ่งครั้งเพื่อพัก กดอีกครั้งเพื่อคืนค่า",
    modeHold: "กดค้าง: กดค้างเพื่อพัก ปล่อยเพื่อคืนค่า",
    networkAdapter: "อะแดปเตอร์เครือข่าย",
    customAdapter: "ชื่ออะแดปเตอร์เอง",
    customAdapterPlaceholder: "ใส่เองถ้าไม่มีในรายการ",
    openUiOnStart: "เปิด Web UI ตอนเริ่มโปรแกรม",
    showNotifications: "แสดงการแจ้งเตือนแบบ toast",
    overlayStartup: "เปิด mini overlay ตอนเริ่มโปรแกรม",
    saveSettings: "บันทึกการตั้งค่า",
    refreshAdapter: "รีเฟรชอะแดปเตอร์",
    running: "กำลังทำงาน",
    stopped: "หยุดแล้ว",
    paused: "พักอยู่",
    readyState: "พร้อมใช้งาน",
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
  if (mode === "hold") {
    return t("modeHoldShort");
  }
  return t("modeToggleShort");
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
  el("openUiOnStart").checked = Boolean(settings.open_ui_on_start);
  el("showNotifications").checked = Boolean(settings.show_notifications);
  el("overlayEnabled").checked = Boolean(settings.overlay_enabled);

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

  const adapterStatus = status.selected_adapter_status;
  el("adapterState").textContent = adapterStatus
    ? `${adapterStatus.name}: ${adapterStatus.admin_state}/${adapterStatus.state}`
    : status.settings.adapter || t("notSelected");

  el("adminStatus").textContent = status.is_admin ? t("administrator") : t("notAdministrator");
  el("adminStatus").className = `status-pill ${status.is_admin ? "ok" : "bad"}`;

  setResult(status.last_result || { ok: true, message: t("ready") });
}

async function refreshStatus(fillForm = false) {
  const status = await api("/api/status");
  renderStatus(status);
  if (fillForm) {
    fillSettings(status);
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
  if (currentStatus) {
    fillSettings(currentStatus);
  }
});

el("refreshButton").addEventListener("click", () => refreshStatus(true));

el("settingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const customAdapter = el("customAdapter").value.trim();
  const payload = {
    hotkey: el("hotkey").value.trim(),
    mode: el("mode").value,
    adapter: customAdapter || el("adapter").value,
    open_ui_on_start: el("openUiOnStart").checked,
    show_notifications: el("showNotifications").checked,
    overlay_enabled: el("overlayEnabled").checked,
  };

  try {
    const result = await api("/api/settings", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setResult({ ok: true, message: t("settingsSaved") });
    currentStatus.settings = result.settings;
  } catch (error) {
    setResult({ ok: false, message: error.message });
  }

  await refreshStatus(true);
});

fillHotkeyOptions();
applyLanguage();
refreshStatus(true);
statusTimer = setInterval(() => refreshStatus(false), 1500);
