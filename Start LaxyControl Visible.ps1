$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppScript = Join-Path $ScriptDir "app.py"
$Requirements = Join-Path $ScriptDir "requirements.txt"
$LogFile = Join-Path $ScriptDir "launcher.log"
$CodexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

Add-Type -AssemblyName System.Windows.Forms | Out-Null

function Write-Log($Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$stamp] $Message"
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-Python {
    if (Test-Path $CodexPython) {
        return $CodexPython
    }

    $pyPath = (& py -3 -c "import sys; print(sys.executable)" 2>$null)
    if ($LASTEXITCODE -eq 0 -and $pyPath -and (Test-Path $pyPath.Trim())) {
        return $pyPath.Trim()
    }

    $pythonPath = (& python -c "import sys; print(sys.executable)" 2>$null)
    if ($LASTEXITCODE -eq 0 -and $pythonPath -and (Test-Path $pythonPath.Trim())) {
        return $pythonPath.Trim()
    }

    return $null
}

function Test-ServiceRunning {
    try {
        $client = New-Object Net.Sockets.TcpClient
        $connected = $client.BeginConnect("127.0.0.1", 8787, $null, $null)
        if ($connected.AsyncWaitHandle.WaitOne(300, $false)) {
            $client.EndConnect($connected)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

if (Test-ServiceRunning) {
    Write-Log "Service already running. Opening Web UI only."
    Start-Process "http://127.0.0.1:8787"
    exit
}

if (-not (Test-Administrator)) {
    Write-Log "Requesting Administrator elevation."
    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile -File `"$PSCommandPath`"" `
        -Verb RunAs
    exit
}

Set-Location $ScriptDir
$PythonExe = Resolve-Python
if (-not $PythonExe) {
    Write-Log "Python was not found."
    [System.Windows.Forms.MessageBox]::Show(
        "Python was not found. Install Python and tick Add Python to PATH.",
        "LaxyControl",
        "OK",
        "Error"
    ) | Out-Null
    exit 1
}

Write-Log "Using Python: $PythonExe"
Write-Host "Using Python: $PythonExe"

$check = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList @("-c", "import keyboard, win10toast") `
    -WorkingDirectory $ScriptDir `
    -Wait `
    -PassThru

if ($check.ExitCode -ne 0) {
    Write-Log "Required packages missing. Installing."
    $pip = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @("-m", "pip", "install", "-r", "`"$Requirements`"") `
        -WorkingDirectory $ScriptDir `
        -Wait `
        -PassThru

    if ($pip.ExitCode -ne 0) {
        Write-Log "Package install failed with exit code $($pip.ExitCode)."
        [System.Windows.Forms.MessageBox]::Show(
            "Failed to install required packages. Check your internet connection and see launcher.log.",
            "LaxyControl",
            "OK",
            "Error"
        ) | Out-Null
        exit $pip.ExitCode
    }
}

Write-Log "Starting app."
Write-Host "Starting LaxyControl in a visible console. Close it with the UI Exit Service button or Ctrl+C."
& $PythonExe $AppScript
