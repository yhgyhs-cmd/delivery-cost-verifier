# Delivery Cost Verifier

Excel-based delivery cost verification tools for:
- Batch verification (`verify_cost.py`)
- Streamlit UI (`app.py`)

## Windows Quick Start

1. Create a virtual environment:
```powershell
python -m venv .venv
```

2. Install dependencies:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Run CLI verification:
```powershell
powershell -ExecutionPolicy Bypass -File .\run_verification.ps1
```

4. Run Streamlit app:
```powershell
powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1
```

5. Run Streamlit without keeping a PowerShell window open:
```powershell
powershell -ExecutionPolicy Bypass -File .\run_streamlit_background.ps1
```

6. Stop background Streamlit:
```powershell
powershell -ExecutionPolicy Bypass -File .\stop_streamlit_background.ps1
```

7. Zero-window launch/stop (double-click):
- `run_streamlit_background.vbs`
- `stop_streamlit_background.vbs`

## What Each Launcher Does

- `run_verification.ps1`
  - Forces working directory to repo root
  - Checks `.venv\Scripts\python.exe`
  - Auto-installs missing runtime packages (`pandas`, `openpyxl`, `streamlit`)
  - Runs `verify_cost.py`

- `run_streamlit.ps1`
  - Uses the same dependency auto-recovery logic
  - Validates `app.py` compilation
  - Runs `python -m streamlit run app.py`

- `run_streamlit_background.ps1`
  - Same dependency and syntax checks
  - Starts Streamlit hidden in background
  - Auto-selects a free port starting at `8501`
  - Saves PID to `.streamlit_background.pid`
  - Writes logs to `streamlit_background.out.log` and `streamlit_background.err.log`

- `stop_streamlit_background.ps1`
  - Stops background Streamlit using PID file and process matching

- `run_streamlit_background.vbs` / `stop_streamlit_background.vbs`
  - Wrapper for true no-console execution on Windows

## Legacy Script

- `run_verification.command` is kept for legacy/macOS Bash workflows.
- On Windows, prefer `run_verification.ps1` and `run_streamlit.ps1`.

## Troubleshooting

### 1) Missing `openpyxl`

Symptom:
- `Missing optional dependency 'openpyxl'`

Fix:
```powershell
.\.venv\Scripts\python.exe -m pip install openpyxl
```

Or just run either `.ps1` launcher; it auto-installs missing packages.

### 2) PowerShell script execution is blocked

Symptom:
- `running scripts is disabled on this system`

Fix for one-time execution:
```powershell
powershell -ExecutionPolicy Bypass -File .\run_verification.ps1
```

Alternative (current shell only):
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_verification.ps1
```
