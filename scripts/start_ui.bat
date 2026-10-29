@echo off
TITLE Antigravity AI - Clean Multi-Agent Dashboard
cd /d "%~dp0\.."

echo ================================================================
echo   Antigravity AI - Clean Multi-Agent Dashboard ^& Knowledge Graph
echo ================================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in .venv
    pause
    exit /b 1
)

if not exist "frontend\dist" (
    echo [*] Building React frontend with Vite...
    cd frontend
    call npm run build
    cd ..
)

echo [OK] Launching Unified Server at http://127.0.0.1:8000
start http://127.0.0.1:8000
".venv\Scripts\python.exe" server.py
pause
