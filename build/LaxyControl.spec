# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).parent
datas = [
    (str(ROOT / "web"), "web"),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "README_TH.md"), "."),
]
windivert_dir = ROOT / "tools" / "windivert"
if windivert_dir.exists():
    datas.append((str(windivert_dir), "tools/windivert"))

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="LaxyControl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(ROOT / "build" / "version_info.txt"),
    manifest=str(ROOT / "build" / "app.manifest"),
    icon=str(ROOT / "assets" / "LaxyControl.ico"),
)
