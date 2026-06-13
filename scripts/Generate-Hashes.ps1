$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$OutFile = Join-Path $Root "dist\SHA256SUMS.txt"
$Targets = @(
    "dist\NetworkControlWebApp.exe",
    "dist\NetworkControlWebAppSetup.exe",
    "README.md",
    "requirements.txt",
    "requirements-build.txt",
    "build\NetworkControlWebApp.spec",
    "build\version_info.txt",
    "build\app.manifest",
    "installer\NetworkControlWebApp.iss"
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
