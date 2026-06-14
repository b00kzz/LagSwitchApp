import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode

from secure_browser import apply_content_protection, hide_from_taskbar


APP_NAME = "LaxyControl"


def api_request(base_url, path, token="", payload=None):
    url = f"{base_url}{path}"
    if payload is None and token:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urlencode({'ui_token': token})}"

    data = None
    headers = {}
    if token:
        headers["Cookie"] = f"laxy_ui_token={token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def run_overlay(base_url, token="", x=40, y=40):
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

    class OverlayWindow(QWidget):
        def __init__(self):
            super().__init__()
            self._hardened = False
            self.setWindowTitle(APP_NAME)
            self.setWindowFlags(
                Qt.WindowStaysOnTopHint
                | Qt.Tool
                | Qt.FramelessWindowHint
            )
            self.setFixedSize(180, 92)
            self.move(x, y)
            self.setStyleSheet(
                """
                QWidget {
                    background: #111827;
                    color: #ffffff;
                    font-family: Segoe UI;
                }
                QPushButton {
                    background: #2563eb;
                    border: 0;
                    border-radius: 4px;
                    color: #ffffff;
                    font-weight: 600;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background: #1d4ed8;
                }
                """
            )

            self.status = QPushButton(f"{APP_NAME} READY", self)
            self.status.setEnabled(False)
            self.toggle = QPushButton("Toggle", self)
            self.toggle.clicked.connect(self.toggle_network)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.addWidget(self.status)
            layout.addWidget(self.toggle)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.refresh)
            self.timer.start(500)
            self.refresh()

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

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

        def mouseMoveEvent(self, event):
            if event.buttons() & Qt.LeftButton and hasattr(self, "_drag_start"):
                self.move(event.globalPosition().toPoint() - self._drag_start)
                event.accept()

        def refresh(self):
            try:
                status = api_request(base_url, "/api/status", token)
            except (OSError, urllib.error.URLError, json.JSONDecodeError):
                self.status.setText(f"{APP_NAME} OFFLINE")
                self.status.setStyleSheet("color: #f87171;")
                return

            paused = bool(status.get("network_paused"))
            self.status.setText(f"{APP_NAME} {'PAUSED' if paused else 'READY'}")
            self.status.setStyleSheet(f"color: {'#dc2626' if paused else '#16a34a'};")

        def toggle_network(self):
            try:
                api_request(base_url, "/api/action", token, {"action": "toggle"})
            except (OSError, urllib.error.URLError, json.JSONDecodeError):
                self.status.setText(f"{APP_NAME} ERROR")
                self.status.setStyleSheet("color: #f87171;")
            self.refresh()

    app = QApplication(sys.argv[:1])
    window = OverlayWindow()
    window.show()
    return app.exec()


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8787"
    token = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        x = int(sys.argv[3]) if len(sys.argv) > 3 else 40
        y = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    except ValueError:
        x, y = 40, 40

    raise SystemExit(run_overlay(base_url, token, x, y))


if __name__ == "__main__":
    main()
