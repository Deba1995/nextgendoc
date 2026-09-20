@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   DocuNext - Offline Bulk Certificate Generator
echo ===================================================

cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your PATH.
    echo Please install Python 3.10+ and make sure it is added to PATH.
    pause
    exit /b 1
)

:: Create virtual environment if it does not exist
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Install requirements if needed
echo [INFO] Ensuring required dependencies are installed...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: Open browser in background after 2 seconds
start "" powershell -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"

:: Launch FastAPI Uvicorn server
echo [INFO] Starting DocuNext server on http://localhost:8000 ...
echo [INFO] Press CTRL+C in this terminal window to stop the server.
echo.
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

pause
