Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PidFile = Join-Path $ScriptDir ".streamlit_background.pid"
$StoppedAny = $false
$TargetApp = (Resolve-Path ".\app.py").Path

if (Test-Path $PidFile) {
    $PidText = (Get-Content -Path $PidFile -Raw).Trim()
    if ($PidText -match "^\d+$") {
        $StreamlitPid = [int]$PidText
        $Process = Get-Process -Id $StreamlitPid -ErrorAction SilentlyContinue
        if ($Process) {
            Stop-Process -Id $StreamlitPid -Force -ErrorAction SilentlyContinue
            Write-Output "[OK] Stopped process by PID: $StreamlitPid"
            $StoppedAny = $true
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

$Candidates = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -match "streamlit" -and
    $_.CommandLine -match "run app\.py" -and
    ($_.CommandLine -like "*$ScriptDir*" -or $_.CommandLine -like "*$TargetApp*")
}

foreach ($Candidate in ($Candidates | Sort-Object ProcessId -Unique)) {
    Stop-Process -Id $Candidate.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Output "[OK] Stopped matched Streamlit process: $($Candidate.ProcessId)"
    $StoppedAny = $true
}

if (-not $StoppedAny) {
    Write-Output "[INFO] No running Streamlit background process found."
}
