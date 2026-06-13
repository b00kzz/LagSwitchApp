param(
    [string]$CertificatePath = $env:NETWORK_CONTROL_CERT_PATH,
    [string]$CertificatePassword = $env:NETWORK_CONTROL_CERT_PASSWORD,
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$Target = "dist\NetworkControlWebApp.exe"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ResolvedTarget = Join-Path $Root $Target

if (-not (Test-Path $ResolvedTarget)) {
    throw "Target not found: $ResolvedTarget"
}

if (-not $CertificatePath) {
    throw "Set NETWORK_CONTROL_CERT_PATH or pass -CertificatePath with your code signing certificate."
}

if (-not (Test-Path $CertificatePath)) {
    throw "Certificate not found: $CertificatePath"
}

$SignTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $SignTool) {
    throw "signtool.exe was not found. Install Windows SDK and retry."
}

$args = @(
    "sign",
    "/fd", "SHA256",
    "/tr", $TimestampUrl,
    "/td", "SHA256",
    "/f", $CertificatePath
)

if ($CertificatePassword) {
    $args += @("/p", $CertificatePassword)
}

$args += $ResolvedTarget

& $SignTool.Source @args
& $SignTool.Source verify /pa /v $ResolvedTarget
