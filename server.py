import uvicorn
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app.api_server import api_app
from app.config import load_config

config = load_config()

# Mount frontend/dist if built for single-server production deployment
frontend_dist = Path(__file__).resolve().parent / "frontend" / "dist"
if frontend_dist.exists():
    api_app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

def start():
    print("==================================================")
    print("  Gemini + Obsidian Multi-Agent Backend Server")
    print("  API Docs: http://127.0.0.1:8000/docs")
    print("==================================================")
    uvicorn.run(api_app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    start()
