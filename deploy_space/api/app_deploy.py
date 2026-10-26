"""One-container entry point: the API plus the built React site, on a single address.
Run:  uvicorn api.app_deploy:app --host 0.0.0.0 --port 7860"""
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from api.app3 import app

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if DIST.exists():                       # must be mounted last: it matches every remaining path
    app.mount("/", StaticFiles(directory=DIST, html=True), name="site")
