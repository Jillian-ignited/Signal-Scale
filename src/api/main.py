# src/api/main.py
from __future__ import annotations
import csv, io, os, json
from typing import Optional, Any, Dict, List

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.orchestrator import run_analysis  # <-- NEW orchestrator

APP_VERSION = "4.0.0"

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.normpath(os.path.join(HERE, "..", "..", "frontend", "dist"))
FRONTEND_DIST = os.environ.get("WEB_DIR", FRONTEND_DIST)

app = FastAPI(title="Signal & Scale", version=APP_VERSION, docs_url="/openapi.json", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ---------- Schemas ----------
class Brand(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class Competitor(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class AnalyzeRequest(BaseModel):
    brand: Brand
    competitors: List[Competitor] = Field(default_factory=list)
    mode: Optional[str] = Field(default="all")
    window_days: Optional[int] = Field(default=7)

# ---------- API ----------
@app.get("/api/health")
async def api_health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": APP_VERSION,
        "frontend_dir": FRONTEND_DIST,
        "frontend_present": os.path.isdir(FRONTEND_DIST),
        "openai_enabled": bool((os.environ.get("OPENAI_API_KEY") or "").strip()),
    }

@app.post("/api/intelligence/analyze")
async def analyze(req: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None, convert_underscores=False)):
    allowed = [k.strip() for k in (os.environ.get("API_KEYS") or "").split(",") if k.strip()]
    if allowed and ((x_api_key or "").strip() not in allowed):
        raise HTTPException(401, "Invalid API key")

    result = await run_analysis(
        brand={"name": req.brand.name, "url": req.brand.url, "meta": req.brand.meta or {}},
        competitors=[{"name": c.name, "url": c.url, "meta": c.meta or {}} for c in req.competitors],
        window_days=req.window_days or 7,
        mode=req.mode or "all",
    )
    return JSONResponse(result)

@app.post("/api/intelligence/export")
async def export_csv(req: AnalyzeRequest):
    result = await run_analysis(
        brand={"name": req.brand.name, "url": req.brand.url, "meta": req.brand.meta or {}},
        competitors=[{"name": c.name, "url": c.url, "meta": c.meta or {}} for c in req.competitors],
        window_days=req.window_days or 7,
        mode=req.mode or "all",
    )
    rows = result.get("signals", [])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["brand", "competitor", "signal", "note", "score", "evidence_type"])
    for s in rows:
        w.writerow([
            s.get("brand"), s.get("competitor") or "",
            s.get("signal"), s.get("note"), s.get("score"),
            (s.get("source") or {}).get("type", ""),
        ])
    bytes_io = io.BytesIO(out.getvalue().encode("utf-8"))
    return StreamingResponse(
        bytes_io,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="signal_scale_export.csv"'},
    )

# ---------- Frontend serving ----------
def _index_path() -> str:
    return os.path.join(FRONTEND_DIST, "index.html")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

@app.get("/", response_class=HTMLResponse)
async def root():
    p = _index_path()
    if not os.path.isfile(p):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: {p}</p>", status_code=404)
    return FileResponse(p)

@app.get("/{path:path}", response_class=HTMLResponse)
async def spa_fallback(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Not found")
    p = _index_path()
    if not os.path.isfile(p):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: {p}</p>", status_code=404)
    return FileResponse(p)

@app.get("/debug", response_class=PlainTextResponse)
async def debug():
    lines = [
        f"version={APP_VERSION}",
        f"FRONTEND_DIST={FRONTEND_DIST}",
        f"exists={os.path.isdir(FRONTEND_DIST)}",
    ]
    try:
        if os.path.isdir(FRONTEND_DIST):
            files = sorted(os.listdir(FRONTEND_DIST))
            lines.append("files=" + ", ".join(files[:40]))
    except Exception as e:
        lines.append(f"ls_error={e}")
    return "\n".join(lines)
