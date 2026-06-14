# LaxyControl

[ภาษาไทย](README_TH.md) | English

Web-first local lag control for Windows. The app runs as a visible local service with a Web UI for testing and settings.

## Quick Start

1. Run `Start LaxyControl.bat` so install/start logs and Administrator prompts stay visible
2. Use `Start LaxyControl Test.bat` only for UI testing without Administrator
3. Approve the Windows Administrator prompt
4. Wait for packages to install
5. The Web UI opens at `http://127.0.0.1:8787`
6. Choose delay, jitter, packet loss, hotkey, and mode
7. Click `Save Settings`

## Launchers

- `Start LaxyControl.bat`: visible console launcher for normal use and debugging.
- `Start LaxyControl Test.bat`: non-admin mode for UI testing only.
- `Start LaxyControl Visible.vbs` / `Start LaxyControl Visible.ps1`: compatibility launchers that redirect to visible startup.

If the service is already running, the launcher opens the Web UI only and does not start another copy.

## How It Works

- Python runs the visible local service.
- The local Web UI is only for testing and configuration.
- Global lag start/stop hotkeys keep working when another app is focused.
- The service is stopped from the Web UI `Exit Service` button.
- The built-in Python lag engine applies delay, jitter, and packet loss through WinDivert without disabling adapters.
- Put `WinDivert.dll` and `WinDivert64.sys` next to `LaxyControl.exe` or at `tools\windivert\` so lag actions can run.
- The Web UI can toggle lag, start lag, stop lag, show overlay, close overlay, or exit the service.
- If the app is already running, launching it again opens the existing Web UI instead of starting another service.
- The Web UI opens in the built-in Secure Browser by default. Direct browser access is blocked with a local token while secure mode is enabled.
- The Secure Browser only allows configured local hosts, hides menus/context actions, blocks common developer-tool shortcuts, and applies Windows content protection with `SetWindowDisplayAffinity`.
- The executable requests Administrator permission at startup through its Windows manifest.
- Web UI start lag, stop lag, toggle, and exit actions ask for confirmation before running.
- Important network actions are appended to `audit.log` for local review.

## Modes

- `Toggle`: press the hotkey once to start lag, press again to stop it.
- `Hold`: hold the hotkey to start lag, release it to stop it.
- `Exit Service`: use the Web UI button to stop the local service.

## Overlay

The mini overlay is optional and runs as a small PySide6 topmost window. It is useful for normal windows and borderless/windowed fullscreen. Some fullscreen apps may cover overlays, so the global hotkey is the main control path.

## Secure Browser

Secure mode is enabled by default through `secure_browser_enabled` in `config.json`. The default allowlist is `127.0.0.1` and `localhost` through `secure_browser_allowed_hosts`.

`SetWindowDisplayAffinity` protects the Secure Browser window from standard Windows screen capture paths where supported. It does not stop external cameras, modified capture drivers, or users with direct access to the local token file.

## Files

- `app.py`: main service, Web UI server, overlay, hotkeys
- `secure_browser.py`: locked PySide6 WebEngine window and Windows content protection
- `overlay_window.py`: PySide6 mini overlay window
- `core/network.py`: adapter list/status and the WinDivert lag engine
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

1. Run `Build Ready.bat` for the full ready build, or run `scripts\Build-Release.ps1` directly.
2. The build installs WinDivert into `tools\windivert`, installs Python requirements, builds the EXE, and prepares the release file.
3. The ready-to-use single-file executable is copied to `release\LaxyControl.exe`.
4. Sign `dist\LaxyControl.exe` with `scripts\Sign-Release.ps1` when you have a code signing certificate.
5. Build `installer\LaxyControl.iss` with Inno Setup if you want an installer.
6. Sign `dist\LaxyControlSetup.exe`.
7. Publish the signed installer or the single-file executable.

Code signing needs your own certificate and Windows SDK `signtool.exe`. Set `LAXYCONTROL_CERT_PATH` and optionally `LAXYCONTROL_CERT_PASSWORD`, or pass `-CertificatePath` and `-CertificatePassword` to `scripts\Sign-Release.ps1`.

The standalone executable is `dist\LaxyControl.exe`. It has no terminal window, requests Administrator permission at startup, bundles the Web UI assets into one file, and opens the Web UI when started. Runtime files such as `config.json` and `audit.log` are created next to the executable so settings and audit history remain reviewable.

For the simplest output, run `Build EXE.bat`. It builds the app and prepares `release\LaxyControl.exe` as the only file you need to run.

## Notes

- Use `Start LaxyControl.bat` for real usage because packet shaping needs Administrator.
- Use `Start LaxyControl Test.bat` only for UI testing and settings.
- Delay, jitter, and packet loss need WinDivert because Windows packet delay/drop requires a driver-level capture path.
- Keep the Web UI, notifications, and audit log available so security tools and users can understand what changed.
