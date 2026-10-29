@echo off
cd /d "%~dp0\.."
echo === Launching Gemini + Obsidian Learning Agents ===
if not exist .venv\Scripts\python.exe (
    echo [ERROR] Virtual environment not found. Please set up .venv first.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
pause
