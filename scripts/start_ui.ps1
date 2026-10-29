# Windows PowerShell Launcher for Antigravity Clean UI & Knowledge Graph
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Antigravity AI — Clean Multi-Agent Dashboard & Knowledge Graph" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at $PythonExe" -ForegroundColor Red
    exit 1
}

# Verify frontend build
$FrontendDist = Join-Path $ProjectRoot "frontend\dist"
if (-not (Test-Path $FrontendDist)) {
    Write-Host "[*] Building React frontend with Vite..." -ForegroundColor Yellow
    Set-Location (Join-Path $ProjectRoot "frontend")
    npm run build
    Set-Location $ProjectRoot
}

Write-Host "[OK] Starting unified server at http://127.0.0.1:8000..." -ForegroundColor Green
Write-Host " - Web Dashboard:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host " - REST API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host " - Press Ctrl+C to stop the server." -ForegroundColor Yellow

Start-Process "http://127.0.0.1:8000"
& $PythonExe server.py
