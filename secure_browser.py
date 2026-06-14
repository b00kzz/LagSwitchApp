import ctypes
import sys
from pathlib import Path
from urllib.parse import urlparse


APP_NAME = "LaxyControl Secure Browser"
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE = -20
SW_HIDE = 0
SW_SHOW = 5
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080


def normalize_hosts(hosts):
    normalized = set()
    for host in hosts or []:
        value = str(host or "").strip().lower()
        if not value:
            continue
        parsed = urlparse(value if "://" in value else f"//{value}")
        normalized.add((parsed.hostname or value).lower())
    return normalized


def apply_content_protection(hwnd):
    if sys.platform != "win32" or not hwnd:
        return False

    user32 = ctypes.windll.user32
    if user32.SetWindowDisplayAffinity(int(hwnd), WDA_EXCLUDEFROMCAPTURE):
        return True
    return bool(user32.SetWindowDisplayAffinity(int(hwnd), WDA_MONITOR))


def hide_from_taskbar(hwnd):
    if sys.platform != "win32" or not hwnd:
        return False

    user32 = ctypes.windll.user32
    handle = int(hwnd)
    get_window_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_window_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    ex_style = get_window_long(handle, GWL_EXSTYLE)
    ex_style = (ex_style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
    user32.ShowWindow(handle, SW_HIDE)
    set_window_long(handle, GWL_EXSTYLE, ex_style)
    user32.ShowWindow(handle, SW_SHOW)
    return True


def icon_path():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    bundled_icon = root / "assets" / "LaxyControl.ico"
    if bundled_icon.exists():
        return bundled_icon
    local_icon = Path(__file__).resolve().parent / "assets" / "LaxyControl.ico"
    return local_icon if local_icon.exists() else None


def transparent_window_icon():
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPixmap

    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    return QIcon(pixmap)


def run_secure_browser(url, allowed_hosts):
    from PySide6.QtCore import Qt, QTimer, QUrl
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView

    allowed = normalize_hosts(allowed_hosts)
    start_host = (urlparse(url).hostname or "").lower()
    if start_host:
        allowed.add(start_host)

    class LockedPage(QWebEnginePage):
        def acceptNavigationRequest(self, target_url, nav_type, is_main_frame):
            host = target_url.host().lower()
            scheme = target_url.scheme().lower()
            if scheme in ("http", "https") and host in allowed:
                return True
            if scheme in ("about", "data") and not is_main_frame:
                return True
            if is_main_frame:
                QMessageBox.warning(None, APP_NAME, f"Blocked navigation to: {target_url.toString()}")
            return False

        def createWindow(self, window_type):
            return None

    class SecureWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self._hardened = False
            self.setWindowTitle(APP_NAME)
            self.resize(1100, 780)
            self.setContextMenuPolicy(Qt.NoContextMenu)
            self.setWindowIcon(transparent_window_icon())

            self.view = QWebEngineView(self)
            self.view.setContextMenuPolicy(Qt.NoContextMenu)
            self.setCentralWidget(self.view)

            profile = QWebEngineProfile("laxycontrol-secure", self.view)
            no_cache = getattr(
                QWebEngineProfile,
                "NoCache",
                QWebEngineProfile.HttpCacheType.NoCache,
            )
            no_persistent_cookies = getattr(
                QWebEngineProfile,
                "NoPersistentCookies",
                QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies,
            )
            profile.setHttpCacheType(no_cache)
            profile.setPersistentCookiesPolicy(no_persistent_cookies)
            profile.downloadRequested.connect(lambda item: item.cancel())

            page = LockedPage(profile, self.view)
            settings = page.settings()
            settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
            settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
            self.view.setPage(page)
            self.view.setUrl(QUrl(url))

            blocked_shortcuts = (
                "F12",
                "Ctrl+Shift+I",
                "Ctrl+Shift+J",
                "Ctrl+Shift+C",
                "Ctrl+U",
                "Ctrl+S",
                "Ctrl+P",
                "Ctrl+O",
            )
            for sequence in blocked_shortcuts:
                shortcut = QShortcut(QKeySequence(sequence), self)
                shortcut.setContext(Qt.ApplicationShortcut)
                shortcut.activated.connect(lambda: None)

        def showEvent(self, event):
            super().showEvent(event)
            QTimer.singleShot(0, self.harden_window)

        def harden_window(self):
            if self._hardened:
                return
            self._hardened = True
            hwnd = int(self.winId())
            hide_from_taskbar(hwnd)
            apply_content_protection(hwnd)

    app = QApplication(sys.argv[:1])
    app.setWindowIcon(transparent_window_icon())
    window = SecureWindow()
    window.show()
    return app.exec()


def main():
    url = "http://127.0.0.1:8787"
    allowed_hosts = ["127.0.0.1", "localhost"]

    args = sys.argv[1:]
    if args:
        url = args[0]
    if len(args) > 1:
        allowed_hosts = [host for host in args[1].split(",") if host.strip()]

    raise SystemExit(run_secure_browser(url, allowed_hosts))


if __name__ == "__main__":
    main()
