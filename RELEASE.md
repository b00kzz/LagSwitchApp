# Release Checklist

Use this checklist for a transparent release process.

1. Build the single-file executable from a clean workspace with `scripts\Build-Release.ps1`.
2. Verify the executable metadata shows `LaxyControl`.
3. Sign `dist\LaxyControl.exe` with `scripts\Sign-Release.ps1`.
4. Build the installer with Inno Setup using `installer\LaxyControl.iss`.
5. Sign `dist\LaxyControlSetup.exe`.
6. Regenerate hashes with `scripts\Generate-Hashes.ps1`.
7. Keep `README.md`, `SHA256SUMS.txt`, and the signed installer together.

## Notes for review

- The app exposes a local Web UI at `127.0.0.1:8787`.
- The Web UI assets are bundled into `LaxyControl.exe`.
- The executable runs without a terminal window and opens the Web UI for user control.
- Duplicate launches open the existing Web UI instead of starting another service.
- Runtime files such as `config.json` and `audit.log` are created next to the executable.
- Network pause/restore actions require explicit user input through the UI, tray menu, or configured hotkey.
- Important actions are written to `audit.log`.
- The app uses visible launchers, tray presence, notifications, and Administrator prompts.
