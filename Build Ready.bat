@echo off
setlocal

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo LaxyControl ready build
echo.
echo This will install WinDivert, install Python requirements, build the EXE,
echo and prepare release\LaxyControl.exe.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\Build-Release.ps1"
if not %errorlevel%==0 (
    echo.
    echo Ready build failed.
    pause
    exit /b 1
)

echo.
echo Ready build complete:
echo "%SCRIPT_DIR%release\LaxyControl.exe"
pause
