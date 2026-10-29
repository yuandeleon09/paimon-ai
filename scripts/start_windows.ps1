# Windows PowerShell Launcher for Gemini Obsidian Learning Agents
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== Starting Gemini + Obsidian Learning Agents (V2) ===" -ForegroundColor Cyan

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at $PythonExe" -ForegroundColor Red
    Write-Host "Please run: py -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

$EnvFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "[WARNING] .env not found. Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvFile
    Write-Host "Please configure your GEMINI_API_KEY in .env" -ForegroundColor Yellow
}

Write-Host "[OK] Launching Streamlit Dashboard at http://localhost:8501..." -ForegroundColor Green
& $PythonExe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
