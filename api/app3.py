"""Run this instead of api.main to get the original endpoints plus the three-carrier
and photo endpoints:  python -m uvicorn api.app3:app --reload --port 8000"""
from api.main import app
from api.photo import router as photo_router
from api.three import router as three_router

app.include_router(three_router)
app.include_router(photo_router)
