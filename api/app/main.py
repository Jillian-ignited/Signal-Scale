# api/app/main.py
from __future__ import annotations
import os
from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Signal & Scale API", version="1.0.0")

# --- CORS ---
# If you want to temporarily allow everything while testing, set ALLOW_ALL_ORIGINS=true in Render env.
ALLOW_ALL = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"

FRONTEND_URL = "https://signal-scale-frontend.onrender.com"   # your static site origin
LOCAL_DEV = "http://localhost:3000"

if ALLOW_ALL:
    allow_origins = ["*"]
    allow_credentials = False  # must be False with "*"
else:
    allow_origins = [FRONTEND_URL, LOCAL_DEV]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],   # includes OPTIONS for preflight
    allow_headers=["*"],   # allows Content-Type, Authorization, etc.
)

# --- Meta/health ---
@app.get("/")
def root():
    return {"name": "Signal & Scale", "status": "operational", "docs_url": "/docs"}

@app.get("/healthz")
def healthz():
    return {"ok": True}

# --- Match your frontend path exactly ---
# Your frontend calls: POST /api/intelligence/analyze
# Keep this stub for now; wire it to your real agents later.
@app.post("/api/intelligence/analyze")
async def analyze(payload: Dict[str, Any]):
    # TODO: call your agent(s) and return real output
    return {"status": "ok", "note": "replace with agent output", "received": payload}
