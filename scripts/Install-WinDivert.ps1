param(
    [string]$Version = "2.2.2-A",
    [string]$DownloadUrl = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ToolsDir = Join-Path $Root "tools\windivert"
$DllPath = Join-Path $ToolsDir "WinDivert.dll"
$SysPath = Join-Path $ToolsDir "WinDivert64.sys"

if (-not $DownloadUrl) {
    $DownloadUrl = "https://reqrypt.org/download/WinDivert-$Version.zip"
}

if ((Test-Path $DllPath) -and (Test-Path $SysPath) -and -not $Force) {
    Write-Host "WinDivert already installed: $ToolsDir"
    exit 0
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("LaxyControl-WinDivert-" + [System.Guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TempRoot "WinDivert.zip"
$ExtractPath = Join-Path $TempRoot "extract"

New-Item -ItemType Directory -Force -Path $TempRoot, $ExtractPath, $ToolsDir | Out-Null

try {
    Write-Host "Downloading WinDivert $Version..."
    Write-Host $DownloadUrl
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath -UseBasicParsing

    Write-Host "Extracting WinDivert..."
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force

    $ExtractedDll = Get-ChildItem -Path $ExtractPath -Recurse -File -Filter "WinDivert.dll" |
        Where-Object { $_.FullName -match "\\x64\\" } |
        Select-Object -First 1
    $ExtractedSys = Get-ChildItem -Path $ExtractPath -Recurse -File -Filter "WinDivert64.sys" |
        Select-Object -First 1

    if (-not $ExtractedDll -or -not $ExtractedSys) {
        throw "Could not find x64 WinDivert.dll and WinDivert64.sys in the downloaded package."
    }

    Copy-Item -LiteralPath $ExtractedDll.FullName -Destination $DllPath -Force
    Copy-Item -LiteralPath $ExtractedSys.FullName -Destination $SysPath -Force

    $Readme = Join-Path $ToolsDir "README.txt"
    @(
        "WinDivert files for LaxyControl",
        "Version: $Version",
        "Source: $DownloadUrl",
        "Required files:",
        "- WinDivert.dll",
        "- WinDivert64.sys",
        "",
        "These files are loaded by the built-in lag engine. Run LaxyControl as Administrator."
    ) | Set-Content -Path $Readme -Encoding UTF8

    Write-Host "WinDivert installed: $ToolsDir"
} finally {
    if (Test-Path $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
