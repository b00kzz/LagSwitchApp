@echo off
net session >nul 2>nul
if not %errorlevel%==0 (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set SCRIPT_DIR=%~dp0
set APP_SCRIPT=%SCRIPT_DIR%app.py
set REQUIREMENTS=%SCRIPT_DIR%requirements.txt
set CODEX_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe

where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=py -3
    goto :run
)

if exist "%CODEX_PYTHON%" (
    set PYTHON_CMD="%CODEX_PYTHON%"
    goto :run
)

where python >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=python
    goto :run
)

echo Python was not found.
echo Install Python from https://www.python.org/downloads/ and tick "Add Python to PATH".
pause
exit /b 1

:run
cd /d "%SCRIPT_DIR%"
echo Installing required packages...
%PYTHON_CMD% -m pip install -r "%REQUIREMENTS%"
if not %errorlevel%==0 (
    echo.
    echo Failed to install required packages.
    echo Check your internet connection, then run this file again.
    pause
    exit /b 1
)

echo.
echo Starting LaxyControl as Administrator...
%PYTHON_CMD% "%APP_SCRIPT%"
pause
