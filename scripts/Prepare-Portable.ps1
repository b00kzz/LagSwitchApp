$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$DistDir = Join-Path $Root "dist"
$ReleaseRoot = Join-Path $Root "release"
$ExePath = Join-Path $DistDir "LaxyControl.exe"
$ReleaseExePath = Join-Path $ReleaseRoot "LaxyControl.exe"
$LegacyPortableDir = Join-Path $ReleaseRoot "LaxyControl-Portable"

if (-not (Test-Path $ExePath)) {
    throw "Build output not found: $ExePath"
}

$Running = Get-Process -Name "LaxyControl" -ErrorAction SilentlyContinue
if ($Running) {
    throw "LaxyControl.exe is still running. Close it from the Web UI Exit button or Task Manager, then prepare the release again."
}

New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null
$ReleaseRootPath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$RootPath = (Resolve-Path -LiteralPath $Root).Path
if (-not $ReleaseRootPath.StartsWith($RootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clean release directory outside workspace: $ReleaseRootPath"
}

Get-ChildItem -LiteralPath $ReleaseRoot -Force | Remove-Item -Recurse -Force
if (Test-Path $LegacyPortableDir) {
    Remove-Item -LiteralPath $LegacyPortableDir -Recurse -Force
}
Copy-Item -LiteralPath $ExePath -Destination $ReleaseExePath -Force

Write-Host "Prepared single-file release: $ReleaseExePath"
