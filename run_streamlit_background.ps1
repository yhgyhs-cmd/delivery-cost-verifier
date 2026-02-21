Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$RequiredPackages = @("pandas", "openpyxl", "streamlit")
$PidFile = Join-Path $ScriptDir ".streamlit_background.pid"
$StdoutLog = Join-Path $ScriptDir "streamlit_background.out.log"
$StderrLog = Join-Path $ScriptDir "streamlit_background.err.log"
$Port = 8501
$MaxPortScan = 20
$TargetApp = (Resolve-Path ".\app.py").Path

function Test-StreamlitPort {
    param([int]$TargetPort)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $TargetPort, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(300)
        if (-not $connected) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-ProjectStreamlitProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match "streamlit" -and
        $_.CommandLine -match "run app\.py" -and
        ($_.CommandLine -like "*$ScriptDir*" -or $_.CommandLine -like "*$TargetApp*")
    }
}

$Existing = Get-ProjectStreamlitProcesses
if ($Existing -and $Existing.Count -gt 0) {
    Write-Output "[OK] This project's Streamlit is already running."
    $IdText = (($Existing | Select-Object -ExpandProperty ProcessId | Sort-Object -Unique) -join ", ")
    Write-Output "PIDs: $IdText"
    if (Test-StreamlitPort -TargetPort $Port) {
        Write-Output "URL: http://127.0.0.1:$Port"
    }
    exit 0
}

if (-not (Test-Path $VenvPython)) {
    Write-Output "[X] Virtual environment not found: .venv\Scripts\python.exe"
    Write-Output "Create it first with:"
    Write-Output "python -m venv .venv"
    exit 1
}

Write-Output "[INFO] Checking required packages..."
$MissingPackages = @()

$InstalledLines = & $VenvPython -m pip list --format=freeze 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Output "[X] Failed to query installed packages."
    exit $LASTEXITCODE
}

$InstalledMap = @{}
foreach ($Line in $InstalledLines) {
    if ($Line -match "^[^=]+==") {
        $Name = $Line.Split("==")[0].ToLowerInvariant()
        $InstalledMap[$Name] = $true
    }
}

foreach ($Package in $RequiredPackages) {
    if (-not $InstalledMap.ContainsKey($Package.ToLowerInvariant())) {
        $MissingPackages += $Package
    }
}

if ($MissingPackages.Count -gt 0) {
    $MissingList = $MissingPackages -join ", "
    Write-Output "[WARN] Missing packages: $MissingList"
    Write-Output "[INFO] Installing missing packages..."

    & $VenvPython -m pip install @MissingPackages
    if ($LASTEXITCODE -ne 0) {
        Write-Output "[X] Failed to install required packages."
        exit $LASTEXITCODE
    }

    Write-Output "[OK] Package installation completed."
} else {
    Write-Output "[OK] All required packages are installed."
}

Write-Output "[INFO] Validating app.py syntax..."
& $VenvPython -m py_compile "app.py"
if ($LASTEXITCODE -ne 0) {
    Write-Output "[X] app.py syntax/import precheck failed."
    exit $LASTEXITCODE
}

Write-Output "[INFO] Starting Streamlit in background..."
$SelectedPort = $Port
for ($i = 0; $i -le $MaxPortScan; $i++) {
    if (-not (Test-StreamlitPort -TargetPort $SelectedPort)) {
        break
    }
    $SelectedPort++
}

if (Test-StreamlitPort -TargetPort $SelectedPort) {
    Write-Output "[X] Could not find a free port in range $Port-$($Port + $MaxPortScan)."
    exit 1
}

if ($SelectedPort -ne $Port) {
    Write-Output "[WARN] Port $Port is busy. Using port $SelectedPort."
}

$Arguments = @(
    "-m", "streamlit", "run", "app.py",
    "--server.headless", "true",
    "--server.address", "127.0.0.1",
    "--server.port", "$SelectedPort"
)

$Proc = Start-Process `
    -FilePath $VenvPython `
    -ArgumentList $Arguments `
    -WorkingDirectory $ScriptDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -PassThru

$Proc.Id | Set-Content -Path $PidFile -Encoding ASCII

$Started = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    if (Test-StreamlitPort -TargetPort $SelectedPort) {
        $Started = $true
        break
    }
    if ($Proc.HasExited) {
        break
    }
}

if ($Started) {
    Write-Output "[OK] Streamlit started in background."
    Write-Output "URL: http://127.0.0.1:$SelectedPort"
    Write-Output "PID: $($Proc.Id)"
    Write-Output "Logs: $StdoutLog"
    exit 0
}

if ($Proc.HasExited) {
    Write-Output "[X] Streamlit exited early. Exit code: $($Proc.ExitCode)"
    Write-Output "See logs:"
    Write-Output "  $StdoutLog"
    Write-Output "  $StderrLog"
    exit 1
}

Write-Output "[WARN] Streamlit process is running, but port check did not succeed yet."
Write-Output "PID: $($Proc.Id)"
Write-Output "Check logs:"
Write-Output "  $StdoutLog"
Write-Output "  $StderrLog"
exit 0
