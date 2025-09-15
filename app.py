import os, io, csv, json, sys
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Signal & Scale", version="2.1.0")

# CORS (safe even if same-origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Auth (per-customer API keys) ----------
def _load_keys(env_name: str) -> List[str]:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]

APP_API_KEYS = _load_keys("API_KEYS")

def require_api_
