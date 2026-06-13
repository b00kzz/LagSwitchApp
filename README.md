# Network Control WebApp

Web-first local network control for Windows. The app runs as a visible local service with a Web UI for testing and settings.

## Quick Start

1. Run `Start Network Control.bat` so install/start logs and Administrator prompts stay visible
2. Use `Start Network Control Test.bat` only for UI testing without Administrator
3. Approve the Windows Administrator prompt
4. Wait for packages to install
5. The Web UI opens at `http://127.0.0.1:8787`
6. Choose adapter, hotkey, and mode
7. Click `Save Settings`

## Launchers

- `Start Network Control.bat`: visible console launcher for normal use and debugging.
- `Start Network Control Test.bat`: non-admin mode for UI testing only.
- `Start Network Control Visible.vbs` / `Start Network Control Visible.ps1`: compatibility launchers that redirect to visible startup.

If the service is already running, the launcher opens the Web UI only and does not start another copy.

## How It Works

- Python runs the visible local service.
- The local Web UI is only for testing and configuration.
- Global network pause/restore hotkeys keep working when another app is focused.
- The service is stopped from the Web UI `Exit Service` button.
- `netsh` restores or pauses the selected adapter/network path.
- The tray icon can open the UI, toggle, pause, restore, show overlay, or close overlay.
- If the app is already running, launching it again opens the existing Web UI instead of starting another service.
- The executable requests Administrator permission at startup through its Windows manifest.
- Web UI pause, restore, toggle, and exit actions ask for confirmation before running.
- Important network actions are appended to `audit.log` for local review.

## Modes

- `Toggle`: press the hotkey once to pause the selected adapter/network path, press again to restore it.
- `Hold`: hold the hotkey to pause the selected adapter/network path, release it to restore it.
- `Exit Service`: use the Web UI button to stop the local service.

## Overlay

The mini overlay is optional. It is useful for normal windows and borderless/windowed fullscreen. Some fullscreen apps may cover overlays, so the global hotkey is the main control path.

## Files

- `app.py`: main service, Web UI server, tray, overlay, hotkeys
- `core/network.py`: adapter list/status/pause/restore
- `core/hotkeys.py`: global hotkey binding
- `core/settings.py`: JSON config
- `web/index.html`: dashboard
- `web/app.js`: API calls and polling
- `web/styles.css`: UI styling
- `build/`: PyInstaller spec, Windows manifest, and executable metadata
- `installer/`: Inno Setup installer definition
- `scripts/`: build, signing, and hash generation helpers
- `RELEASE.md`: release checklist and review notes

## Build and Release

1. Build the single-file executable with `scripts\Build-Release.ps1`.
2. Sign `dist\NetworkControlWebApp.exe` with `scripts\Sign-Release.ps1`.
3. Build `installer\NetworkControlWebApp.iss` with Inno Setup.
4. Sign `dist\NetworkControlWebAppSetup.exe`.
5. Publish the signed installer with `dist\SHA256SUMS.txt`, `README.md`, and `RELEASE.md`.

Code signing needs your own certificate and Windows SDK `signtool.exe`. Set `NETWORK_CONTROL_CERT_PATH` and optionally `NETWORK_CONTROL_CERT_PASSWORD`, or pass `-CertificatePath` and `-CertificatePassword` to `scripts\Sign-Release.ps1`.

The standalone executable is `dist\NetworkControlWebApp.exe`. It has no terminal window, requests Administrator permission at startup, bundles the Web UI assets into one file, and opens the Web UI when started. Runtime files such as `config.json` and `audit.log` are created next to the executable so settings and audit history remain reviewable.

## Notes

- Use `Start Network Control.bat` for real usage because adapter control needs Administrator.
- Use `Start Network Control Test.bat` only for UI testing and settings.
- If USB tethering does not appear, connect the phone and enable USB tethering before refreshing adapters.
- Avoid non-visible launch for normal use. The app intentionally keeps its UI, tray icon, notifications, and audit log available so security tools and users can understand what changed.
