# api/app/main.py
from __future__ import annotations
import os
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

APP_NAME = os.getenv("APP_NAME", "Signal & Scale API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

app = FastAPI(title=APP_NAME, version=APP_VERSION, docs_url="/docs", redoc_url=None)

# CORS toggles via env
ALLOW_ALL = os.getenv("ALLOW_ALL_ORIGINS", "false").strip().lower() == "true"
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://signal-scale-frontend.onrender.com,http://localhost:5173",
)

allow_origins = ["*"] if ALLOW_ALL else [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
allow_credentials = False if ALLOW_ALL else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[REQ] {request.method} {request.url.path} | Origin={request.headers.get('origin','-')}")
    resp = await call_next(request)
    print(f"[RES] {request.method} {request.url.path} | "
          f"ACAO={resp.headers.get('access-control-allow-origin','-')} | Status={resp.status_code}")
    return resp

@app.get("/")
def root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "operational",
        "environment": os.getenv("ENV", "development"),
        "docs_url": "/docs",
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/api/meta")
def api_meta():
    return {"api": "ok", "version": APP_VERSION}

# Stub endpoints your frontend calls
@app.options("/api/intelligence/analyze")
async def options_analyze():
    return JSONResponse({"ok": True})

@app.post("/api/intelligence/analyze")
async def intelligence_analyze(payload: Dict[str, Any]):
    return {
        "status": "ok",
        "endpoint": "/api/intelligence/analyze",
        "received": payload,
        "note": "stub response: replace with agent output",
    }

@app.post("/api/run/cultural_radar")
async def run_cultural_radar(payload: Dict[str, Any]):
    return {
        "status": "ok",
        "endpoint": "/api/run/cultural_radar",
        "received": payload,
        "note": "stub response: replace with cultural radar agent",
    }

@app.post("/api/run/competitive_playbook")
async def run_competitive_playbook(payload: Dict[str, Any]):
    return {
        "status": "ok",
        "endpoint": "/api/run/competitive_playbook",
        "received": payload,
        "note": "stub response: replace with competitive playbook agent",
    }
