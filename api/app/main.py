# api/app/main.py
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

# ---- Settings (lightweight, no extra deps) ----------------------------------
ENV = os.getenv("ENV", "development")
APP_NAME = os.getenv("APP_NAME", "Signal & Scale")
TZ = os.getenv("TZ", "America/Chicago")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # used by agent services

# Comma-separated origins, or fallback to common defaults
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "https://signal-scale-frontend.onrender.com,http://localhost:3000"
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ---- App init ----------------------------------------------------------------
app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
    description="Signal & Scale API – cultural radar, competitive playbook, and DTC audit",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,     # set False if you don't use cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Optional agent imports (defensive) --------------------------------------
# Cultural Radar
try:
    from .agents.cultural_radar import run_cultural_radar as _run_cultural
except Exception as e:
    _run_cultural = None
    _cultural_import_err = str(e)

# Competitive Playbook (optional; handled gracefully if not present)
try:
    from .agents.competitive_playbook import run_competitive_playbook as _run_competitive
except Exception as e:
    _run_competitive = None
    _competitive_import_err = str(e)

# DTC Audit (optional; handled gracefully if not present)
try:
    from .agents.dtc_audit import run_dtc_audit as _run_dtc
except Exception as e:
    _run_dtc = None
    _dtc_import_err = str(e)

# ---- Utilities ---------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _require_agent(agent_fn, agent_name: str, import_err: Optional[str] = None):
    if agent_fn is None:
        msg = f"Agent '{agent_name}' is not available. Import failed."
        if import_err:
            msg += f" Details: {import_err}"
        raise HTTPException(status_code=503, detail=msg)

def _require_openai():
    if not OPENAI_API_KEY:
        # Don’t crash — return a 200 with a guidance payload so FE can still render
        return False
    return True

def _ok_mock(payload: Dict[str, Any], note: str) -> Dict[str, Any]:
    return {
        "status": "ok",
        "mock": True,
        "note": note,
        "received": payload,
        "generated_at": _now_iso(),
    }

# ---- Root & health -----------------------------------------------------------
@app.get("/", tags=["meta"])
def root() -> Dict[str, Any]:
    """Friendly status JSON (handy for quick checks)."""
    return {
        "name": APP_NAME,
        "version": "1.0.0",
        "status": "operational",
        "environment": ENV,
        "timestamp": _now_iso(),
        "docs_url": "/docs",
    }

@app.get("/healthz", tags=["meta"])
def healthz() -> Dict[str, Any]:
    return {"ok": True, "timestamp": _now_iso()}

# ---- Cultural Radar ----------------------------------------------------------
@app.post("/api/run/cultural_radar", tags=["agents"])
async def api_run_cultural_radar(payload: Dict[str, Any]) -> JSONResponse:
    """
    Runs the Cultural Radar agent.
    Expects: { brand, competitors, window, ... }
    """
    _require_agent(_run_cultural, "cultural_radar", globals().get("_cultural_import_err"))
    if not _require_openai():
        return JSONResponse(
            _ok_mock(payload, "OPENAI_API_KEY not set; returning mock response."),
            status_code=200
        )
    try:
        data = await _run_cultural(payload)
        # Ensure consistent footer fields if agent didn't add them
        data.setdefault("confidence_footer", {
            "confidence": "medium",
            "variance": 0.0,
            "window": payload.get("window"),
            "sources": ["web", "social", "retail"],
        })
        return JSONResponse(data, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"cultural_radar failed: {e}")

# ---- Competitive Playbook ----------------------------------------------------
@app.post("/api/run/competitive_playbook", tags=["agents"])
async def api_run_competitive_playbook(payload: Dict[str, Any]) -> JSONResponse:
    """
    Runs the Competitive Playbook agent.
    Expects: { brand, competitors, window, ... }
    """
    if _run_competitive is None:
        # Graceful placeholder so the FE doesn’t break if this agent isn’t wired yet.
        return JSONResponse(
            _ok_mock(payload, "competitive_playbook agent not present; returning placeholder."),
            status_code=200
        )
    if not _require_openai():
        return JSONResponse(
            _ok_mock(payload, "OPENAI_API_KEY not set; returning mock response."),
            status_code=200
        )
    try:
        data = await _run_competitive(payload)
        return JSONResponse(data, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"competitive_playbook failed: {e}")

# ---- DTC Audit ---------------------------------------------------------------
@app.post("/api/run/dtc_audit", tags=["agents"])
async def api_run_dtc_audit(payload: Dict[str, Any]) -> JSONResponse:
    """
    Runs the DTC Audit agent.
    Expects: { brand, competitors?, window?, ... }
    """
    if _run_dtc is None:
        return JSONResponse(
            _ok_mock(payload, "dtc_audit agent not present; returning placeholder."),
            status_code=200
        )
    if not _require_openai():
        return JSONResponse(
            _ok_mock(payload, "OPENAI_API_KEY not set; returning mock response."),
            status_code=200
        )
    try:
        data = await _run_dtc(payload)
        return JSONResponse(data, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"dtc_audit failed: {e}")

# ---- Export (simple) ---------------------------------------------------------
@app.post("/api/export", tags=["export"])
def api_export(payload: Dict[str, Any]) -> Response:
    """
    Export helper.
    Body: { "format": "json"|"html"|"md", "data": {...} }
    Returns a file download.
    """
    fmt = str(payload.get("format", "json")).lower()
    data = payload.get("data", {})
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    if fmt == "json":
        return JSONResponse(
            data,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="signal-scale-{ts}.json"'},
        )

    if fmt == "md":
        body = [
            f"# {APP_NAME} Report",
            f"_Generated: {datetime.now().isoformat()}_",
            "",
            "```json",
            json.dumps(data, indent=2),
            "```",
            "",
        ]
        md = "\n".join(body)
        return PlainTextResponse(
            md,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="signal-scale-{ts}.md"'},
        )

    if fmt == "html":
        html = f"""<!doctype html>
<html><head><meta charset="utf-8" />
<title>{APP_NAME} Report</title>
<style>
 body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial;margin:40px;color:#111}}
 h1,h2{{margin:0 0 8px}}
 .muted{{color:#666}}
 .card{{border:1px solid #eee;border-radius:12px;padding:16px;margin:12px 0}}
 pre{{white-space:pre-wrap;word-wrap:break-word}}
</style>
</head><body>
  <h1>{APP_NAME} Report</h1>
  <p class="muted">Generated: {datetime.now().isoformat()}</p>
  <div class="card">
    <h2>Executive Summary</h2>
    <pre>{json.dumps(data.get("executive_summary", data), indent=2)}</pre>
  </div>
  <div class="card">
    <h2>Details</h2>
    <pre>{json.dumps(data, indent=2)}</pre>
  </div>
</body></html>"""
        return Response(
            content=html,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="signal-scale-{ts}.html"'},
        )

    raise HTTPException(status_code=400, detail="Unsupported format. Use json|md|html.")
