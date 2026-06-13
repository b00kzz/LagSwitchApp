$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$DistDir = Join-Path $Root "dist"
$ReleaseRoot = Join-Path $Root "release"
$PortableDir = Join-Path $ReleaseRoot "LaxyControl-Portable"
$ExePath = Join-Path $DistDir "LaxyControl.exe"

if (-not (Test-Path $ExePath)) {
    throw "Build output not found: $ExePath"
}

if (Test-Path $PortableDir) {
    Remove-Item -LiteralPath $PortableDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $PortableDir | Out-Null

$CopyItems = @(
    @{ Source = "dist\LaxyControl.exe"; Target = "LaxyControl.exe" },
    @{ Source = "README.md"; Target = "README.md" },
    @{ Source = "README_TH.md"; Target = "README_TH.md" },
    @{ Source = "RELEASE.md"; Target = "RELEASE.md" },
    @{ Source = "assets\LaxyControl.ico"; Target = "LaxyControl.ico" }
)

if (Test-Path (Join-Path $Root "config.json")) {
    $CopyItems += @{ Source = "config.json"; Target = "config.json" }
}

foreach ($Item in $CopyItems) {
    $Source = Join-Path $Root $Item.Source
    $Target = Join-Path $PortableDir $Item.Target
    if (Test-Path $Source) {
        Copy-Item -LiteralPath $Source -Destination $Target -Force
    }
}

$HashTargets = Get-ChildItem -LiteralPath $PortableDir -File | Sort-Object Name
$HashLines = foreach ($File in $HashTargets) {
    $Hash = Get-FileHash -Algorithm SHA256 -LiteralPath $File.FullName
    "$($Hash.Hash.ToLowerInvariant())  $($File.Name)"
}

$HashLines | Set-Content -Path (Join-Path $PortableDir "SHA256SUMS.txt") -Encoding ascii

Write-Host "Prepared portable folder: $PortableDir"
