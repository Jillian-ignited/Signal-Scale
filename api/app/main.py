# api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import intelligence  # <-- our only router for now
import os

app = FastAPI(title="Signal & Scale API", version="1.0.0")

# --- CORS (allow your frontend domain + localhost for dev) ---
FRONTEND_ORIGINS = [
    "https://signal-scale-frontend.onrender.com",
    "https://signal-scale.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount routers under a single /api prefix ---
# IMPORTANT: the router itself must NOT also include "/api" in its prefix.
app.include_router(intelligence.router, prefix="/api")

@app.get("/healthz")
def health():
    return {
        "status": "ok",
        "service": "signal-scale",
        "env": os.getenv("ENV", "development")
    }

# For Render's gunicorn import path `api.app.main:app`
# no if __name__ == "__main__" block needed.