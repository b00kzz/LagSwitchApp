$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Set-Location $Root
Write-Host "Installing runtime requirements..."
& $Python -m pip install -r requirements.txt

Write-Host "Installing build requirements..."
& $Python -m pip install -r requirements-build.txt

Write-Host "Building LaxyControl as a single-file executable..."
& $Python -m PyInstaller --clean --noconfirm build\LaxyControl.spec

Write-Host "Preparing single-file release..."
& powershell -NoProfile -File scripts\Prepare-Portable.ps1

Write-Host "Build complete: release\LaxyControl.exe"
Write-Host "Runtime config and audit files will be created next to the executable when it runs."
