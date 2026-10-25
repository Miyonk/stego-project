"""Run this instead of api.main to get the original endpoints plus the three-carrier ones:
python -m uvicorn api.app3:app --reload --port 8000"""
from api.main import app
from api.three import router

app.include_router(router)
