Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$RequiredPackages = @("pandas", "openpyxl", "streamlit")

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

Write-Output "[INFO] Starting Streamlit app..."
& $VenvPython -m streamlit run "app.py"
$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Output "[OK] Streamlit app exited successfully."
} else {
    Write-Output "[X] Streamlit failed to start or crashed. Exit code: $ExitCode"
    Write-Output "[INFO] Check the error output above for app import/runtime details."
}

Write-Output "[INFO] Finished."
exit $ExitCode
