# api/app/main.py
from __future__ import annotations
import os
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# -------- App meta (can be overridden via env) --------
APP_NAME = os.getenv("APP_NAME", "Signal & Scale API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# -------- CORS configuration --------
# Quick debug switch (set in Render env while troubleshooting)
ALLOW_ALL = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"

# Comma-separated list is supported (e.g., "https://your-frontend, http://localhost:5173")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://signal-scale-frontend.onrender.com,http://localhost:5173"
)

if ALLOW_ALL:
    allow_origins = ["*"]
    allow_credentials = False  # Wildcard cannot be used with credentials
else:
    allow_origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],   # includes OPTIONS for preflight
    allow_headers=["*"],   # e.g., Content-Type, Authorization
)

# -------- Simple request logging (helps debug Origins/CORS) --------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get("origin", "-")
    path = request.url.path
    method = request.method
    host = request.headers.get("host", "-")
    print(f"[REQ] {method} {path} | Origin={origin} | Host={host}")
    response = await call_next(request)
    try:
        acao = response.headers.get("access-control-allow-origin", "-")
        print(f"[RES] {method} {path} | ACAO={acao} | Status={response.status_code}")
    except Exception:
        pass
    return response

# -------- Meta / health --------
@app.get("/")
def root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "operational",
        "docs_url": "/docs",
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}

# -------- API endpoints expected by your frontend --------
# 1) Dynamic analysis (used in your dashboard)
@app.post("/api/intelligence/analyze")
async def analyze(payload: Dict[str, Any]):
    # TODO: replace with real agent orchestration
    return {
        "status": "ok",
        "endpoint": "/api/intelligence/analyze",
        "received": payload,
        "note": "stub response: wire your agent here",
    }

# 2) Cultural Radar (optional stub for now)
@app.post("/api/run/cultural_radar")
async def run_cultural_radar(payload: Dict[str, Any]):
    # TODO: call your cultural radar agent
    return {
        "status": "ok",
        "endpoint": "/api/run/cultural_radar",
        "received": payload,
        "note": "stub response: wire cultural radar here",
    }

# 3) Competitive Playbook (optional stub for now)
@app.post("/api/run/competitive_playbook")
async def run_competitive_playbook(payload: Dict[str, Any]):
    # TODO: call your competitive playbook agent
    return {
        "status": "ok",
        "endpoint": "/api/run/competitive_playbook",
        "received": payload,
        "note": "stub response: wire competitive playbook here",
    }
