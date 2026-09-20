# DocuNext PowerShell Launcher
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  DocuNext - Offline Bulk Certificate Generator" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python was not found in your PATH. Please install Python 3.10+."
    exit 1
}

# Setup venv if needed
$venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[INFO] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
}

# Install requirements
Write-Host "[INFO] Checking Python dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install -q -r requirements.txt

# Start browser delayed
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:8000"
} | Out-Null

# Start server
Write-Host "[INFO] Starting DocuNext at http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "[INFO] Press Ctrl+C to exit." -ForegroundColor Gray
& $venvPython -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
