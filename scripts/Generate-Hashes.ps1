$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$OutFile = Join-Path $Root "dist\SHA256SUMS.txt"
$Targets = @(
    "dist\LaxyControl.exe",
    "dist\LaxyControlSetup.exe",
    "README.md",
    "README_TH.md",
    "requirements.txt",
    "requirements-build.txt",
    "build\LaxyControl.spec",
    "build\version_info.txt",
    "build\app.manifest",
    "assets\LaxyControl.ico",
    "installer\LaxyControl.iss"
)

$Lines = foreach ($RelativePath in $Targets) {
    $Path = Join-Path $Root $RelativePath
    if (Test-Path $Path) {
        $Hash = Get-FileHash -Algorithm SHA256 -LiteralPath $Path
        "$($Hash.Hash.ToLowerInvariant())  $RelativePath"
    }
}

$Lines | Set-Content -Path $OutFile -Encoding ascii
Write-Host "Wrote $OutFile"
