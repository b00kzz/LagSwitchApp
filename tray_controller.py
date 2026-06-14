import sys

from secure_browser import icon_path, transparent_window_icon


def run_tray(app):
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

    qt_app = QApplication.instance() or QApplication(sys.argv[:1])
    qt_app.setQuitOnLastWindowClosed(False)

    app_icon = icon_path()
    tray_icon = QIcon(str(app_icon)) if app_icon else transparent_window_icon()
    qt_app.setWindowIcon(tray_icon)

    tray = QSystemTrayIcon(tray_icon, qt_app)
    tray.setToolTip("LaxyControl")

    menu = QMenu()
    open_action = menu.addAction("Open Web UI")
    toggle_action = menu.addAction("Toggle Network")
    pause_action = menu.addAction("Pause")
    restore_action = menu.addAction("Restore")
    menu.addSeparator()
    show_overlay_action = menu.addAction("Show Overlay")
    close_overlay_action = menu.addAction("Hide Overlay")
    menu.addSeparator()
    exit_action = menu.addAction("Exit")

    def refresh_tooltip():
        status = app.status()
        network = "Paused" if status.get("network_paused") else "Ready"
        hotkey = status.get("settings", {}).get("hotkey", "-")
        mode = status.get("settings", {}).get("mode", "toggle")
        tray.setToolTip(f"LaxyControl\nNetwork: {network}\nHotkey: {hotkey} ({mode})")

    def run_action(callback):
        try:
            callback()
        finally:
            refresh_tooltip()

    open_action.triggered.connect(lambda: run_action(app.open_ui))
    toggle_action.triggered.connect(lambda: run_action(lambda: app.toggle("tray")))
    pause_action.triggered.connect(lambda: run_action(lambda: app.pause_network("tray")))
    restore_action.triggered.connect(lambda: run_action(lambda: app.restore_network("tray")))
    show_overlay_action.triggered.connect(lambda: run_action(app.overlay.show))
    close_overlay_action.triggered.connect(lambda: run_action(app.overlay.close))

    def exit_app():
        app.shutdown()
        tray.hide()
        qt_app.quit()

    exit_action.triggered.connect(exit_app)
    tray.activated.connect(
        lambda reason: app.open_ui()
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick
        else None
    )
    tray.setContextMenu(menu)
    tray.show()

    timer = QTimer()
    timer.timeout.connect(refresh_tooltip)
    timer.start(1500)
    refresh_tooltip()

    return qt_app.exec()
