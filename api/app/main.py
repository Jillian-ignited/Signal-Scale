# api/app/main.py
from __future__ import annotations
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

APP_NAME = os.getenv("APP_NAME", "Signal & Scale API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
ENV = os.getenv("ENV", "development")

# ── CORS: allow all while debugging; lock down later via ALLOWED_ORIGINS
ALLOW_ALL = os.getenv("ALLOW_ALL_ORIGINS", "true").strip().lower() == "true"
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://signal-scale-frontend.onrender.com,http://localhost:5173",
)

allow_origins = ["*"] if ALLOW_ALL else [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
allow_credentials = False if ALLOW_ALL else True

app = FastAPI(title=APP_NAME, version=APP_VERSION, docs_url="/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Simple request/response log to help debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[REQ] {request.method} {request.url.path} | Origin={request.headers.get('origin','-')}")
    resp = await call_next(request)
    print(f"[RES] {request.method} {request.url.path} | "
          f"ACAO={resp.headers.get('access-control-allow-origin','-')} | Status={resp.status_code}")
    return resp

# ── Health/meta
@app.get("/")
def root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "operational",
        "environment": ENV,
        "docs_url": "/docs",
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/api/meta")
def api_meta():
    return {"api": "ok", "version": APP_VERSION, "env": ENV}

# ── OPTIONS handler to satisfy browser preflight
@app.options("/api/intelligence/analyze")
async def options_analyze():
    return JSONResponse({"ok": True})

# ── UI-friendly ANALYZE endpoint (this fixes “Analysis failed” in the frontend)
@app.post("/api/intelligence/analyze")
async def intelligence_analyze(payload: Dict[str, Any] = Body(...)):
    """
    Returns a stable, frontend-friendly shape so the dashboard can render without errors.
    Replace this stub content with your real agent output later.
    """
    now = datetime.utcnow().isoformat() + "Z"
    received = payload or {}
    return {
        "success": True,
        "message": "ok",
        "timestamp": now,
        "meta": {
            "brand": received.get("brand", "Unknown"),
            "environment": ENV,
        },
        "confidence": {
            "score": 0.9,
            "range": "High",
            "variance": 0.05
        },
        "sources": [
            {"type": "internal", "name": "bootstrap-stub", "count": 0}
        ],
        "report": {
            "title": "Dynamic Cultural Intelligence (Stub)",
            "summary": "Wiring check successful. Replace this with real agent output.",
            "highlights": [
                "Pipeline connected end-to-end",
                "Frontend calling correct backend",
                "Response matches expected shape"
            ],
            "metrics": {
                "mentions_week": 18,
                "sentiment_positive_pct": 75,
                "top_trends": ["Ralphcore", "Wide Leg Trousers", "Sustainable Streetwear"]
            },
            "actions": [
                {"priority": "High", "label": "Seed 2 creators on trending tag"},
                {"priority": "Medium", "label": "Lower free-shipping threshold test"}
            ],
        },
        "raw": {"received_input": received}
    }

# ── Stubs for your other buttons so UI won’t break
@app.post("/api/run/cultural_radar")
async def run_cultural_radar(payload: Dict[str, Any] = Body(...)):
    return {
        "success": True,
        "endpoint": "/api/run/cultural_radar",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "report": {"title": "Cultural Radar (Stub)", "summary": "Replace with agent output"},
    }

@app.post("/api/run/competitive_playbook")
async def run_competitive_playbook(payload: Dict[str, Any] = Body(...)):
    return {
        "success": True,
        "endpoint": "/api/run/competitive_playbook",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "report": {"title": "Competitive Playbook (Stub)", "summary": "Replace with agent output"},
    }
