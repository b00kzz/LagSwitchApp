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

Write-Host "Generating release hashes..."
& powershell -NoProfile -File scripts\Generate-Hashes.ps1

Write-Host "Preparing portable folder..."
& powershell -NoProfile -File scripts\Prepare-Portable.ps1

Write-Host "Build complete: dist\LaxyControl.exe"
Write-Host "Portable folder: release\LaxyControl-Portable"
Write-Host "Runtime config and audit files will be created next to the executable when it runs."
