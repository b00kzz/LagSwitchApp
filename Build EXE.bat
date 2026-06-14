@echo off
setlocal

set SCRIPT_DIR=%~dp0
set REQUIREMENTS=%SCRIPT_DIR%requirements.txt
set BUILD_REQUIREMENTS=%SCRIPT_DIR%requirements-build.txt
set SPEC_FILE=%SCRIPT_DIR%build\LaxyControl.spec
set CODEX_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe

cd /d "%SCRIPT_DIR%"

where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=py -3
    goto :build
)

where python >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=python
    goto :build
)

if exist "%CODEX_PYTHON%" (
    set PYTHON_CMD="%CODEX_PYTHON%"
    goto :build
)

echo Python was not found.
echo Install Python from https://www.python.org/downloads/ and tick "Add Python to PATH".
pause
exit /b 1

:build
echo Using Python: %PYTHON_CMD%
echo.

tasklist /FI "IMAGENAME eq LaxyControl.exe" 2>nul | find /I "LaxyControl.exe" >nul
if %errorlevel%==0 (
    echo LaxyControl.exe is still running.
    echo Close it from the Web UI Exit button or Task Manager, then run this build again.
    pause
    exit /b 1
)

echo Installing runtime requirements...
%PYTHON_CMD% -m pip install -r "%REQUIREMENTS%"
if not %errorlevel%==0 (
    echo.
    echo Failed to install runtime requirements.
    pause
    exit /b 1
)

echo.
echo Installing build requirements...
%PYTHON_CMD% -m pip install -r "%BUILD_REQUIREMENTS%"
if not %errorlevel%==0 (
    echo.
    echo Failed to install build requirements.
    pause
    exit /b 1
)

echo.
echo Building single-file EXE...
%PYTHON_CMD% -m PyInstaller --clean --noconfirm "%SPEC_FILE%"
if not %errorlevel%==0 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Preparing single-file release...
powershell -NoProfile -File "%SCRIPT_DIR%scripts\Prepare-Portable.ps1"
if not %errorlevel%==0 (
    echo.
    echo Single-file release preparation failed.
    pause
    exit /b 1
)

echo.
echo Done.
echo EXE: "%SCRIPT_DIR%dist\LaxyControl.exe"
echo Single-file release: "%SCRIPT_DIR%release\LaxyControl.exe"
echo Runtime config and audit files will be created next to the EXE when it runs.
pause
