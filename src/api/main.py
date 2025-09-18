# src/api/main.py
from __future__ import annotations

import csv
import io
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_VERSION = "3.2.0"

# --- Paths (repo: frontend/ + src/api/) ---
HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.normpath(os.path.join(HERE, "..", "..", "frontend", "dist"))
# Allow override via env if you ever need it
FRONTEND_DIST = os.environ.get("WEB_DIR", FRONTEND_DIST)

app = FastAPI(title="Signal & Scale", version=APP_VERSION, docs_url="/openapi.json", redoc_url=None)

# CORS (relax now, tighten later to your domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
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

# ---------- Helpers ----------
def _hostish(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip()
    if s.startswith("http"):
        h = re.sub(r"^https?://", "", s).split("/")[0].replace("www.", "").split(":")[0]
        return h
    return s

async def quick_probe(url: Optional[str]) -> Dict[str, Any]:
    """Fast GET to detect basic UX/payment signals + rough latency."""
    info = {
        "reachable": False,
        "status": None,
        "server": None,
        "shop_pay": False,
        "apple_pay": False,
        "klarna": False,
        "latency_ms": None,
    }
    if not url:
        return info
    if not url.startswith("http"):
        url = "https://" + url

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(6.0, connect=3.0),
            follow_redirects=True,
            headers={"User-Agent": "SignalScale/1.0"}
        ) as client:
            r = await client.get(url)
            info["status"] = r.status_code
            info["server"] = r.headers.get("server")
            info["reachable"] = 200 <= r.status_code < 400
            text = (r.text or "")[:120_000].lower()
            info["shop_pay"] = ("shop pay" in text) or ("shop.app/pay" in text)
            info["apple_pay"] = ("apple pay" in text) or ("apple-pay" in text)
            info["klarna"] = "klarna" in text
    except Exception:
        pass
    info["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return info

def synthesize(brand: Brand, comps: List[Competitor], probes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Heuristic deltas that differ by each competitor; solid baseline until you wire deeper data."""
    bname = brand.name or _hostish(brand.url) or "Brand"
    summary = {"brand": bname, "competitors": [c.name or _hostish(c.url) for c in comps]}

    signals: List[Dict[str, Any]] = []
    bp = probes.get("brand") or {}

    for c in comps:
        cname = c.name or _hostish(c.url) or "Competitor"
        key = cname.lower()
        cp = probes.get(key) or {}

        # Trust/payments
        b_pay = any([bp.get("shop_pay"), bp.get("apple_pay"), bp.get("klarna")])
        c_pay = any([cp.get("shop_pay"), cp.get("apple_pay"), cp.get("klarna")])
        if c_pay and not b_pay:
            signals.append({
                "brand": bname,
                "competitor": cname,
                "signal": "Checkout trust gap",
                "note": f"{cname} exposes accelerated pay (Shop Pay / Apple Pay / Klarna). Add & surface above-the-fold on PDP.",
                "score": 82,
                "source": {"probe": "payments"},
            })
        if b_pay and not c_pay:
            signals.append({
                "brand": bname,
                "competitor": cname,
                "signal": "Trust advantage",
                "note": f"You surface accelerated pay; emphasize badges near ATC and in mini-cart.",
                "score": 68,
                "source": {"probe": "payments"},
            })

        # Performance
        b_lat, c_lat = bp.get("latency_ms"), cp.get("latency_ms")
        if isinstance(b_lat, int) and isinstance(c_lat, int) and c_lat + 200 < b_lat:
            signals.append({
                "brand": bname,
                "competitor": cname,
                "signal": "Performance gap",
                "note": f"{cname} homepage loads faster (~{c_lat}ms vs {b_lat}ms). Audit hero weight, lazy-load below-the-fold JS.",
                "score": 74,
                "source": {"probe": "latency"},
            })

        # Availability
        if cp.get("reachable") and not bp.get("reachable"):
            signals.append({
                "brand": bname,
                "competitor": cname,
                "signal": "Availability gap",
                "note": f"{cname} reachable while your site appears down. Check DNS, CDN, and origin health.",
                "score": 76,
                "source": {"probe": "reachability"},
            })

    if not signals:
        signals.append({
            "brand": bname,
            "competitor": None,
            "signal": "Baseline",
            "note": "No obvious deltas from quick probes. Next: PDP content audit (video, materials, fit guide, UGC, cross-sell).",
            "score": 50,
            "source": {"probe": "baseline"},
        })

    return {"ok": True, "summary": summary, "signals": signals, "probes": probes}

# ---------- API ----------
@app.get("/api/health")
async def api_health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": APP_VERSION,
        "frontend_dir": FRONTEND_DIST,
        "frontend_present": os.path.isdir(FRONTEND_DIST),
    }

@app.post("/api/intelligence/analyze")
async def analyze(req: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None, convert_underscores=False)):
    # Optional key gate: set API_KEYS="key1,key2" in Render to enable
    allowed = [k.strip() for k in (os.environ.get("API_KEYS") or "").split(",") if k.strip()]
    if allowed and ((x_api_key or "").strip() not in allowed):
        raise HTTPException(401, "Invalid API key")

    probes: Dict[str, Dict[str, Any]] = {}
    probes["brand"] = await quick_probe(req.brand.url)
    for c in req.competitors:
        key = (c.name or _hostish(c.url) or "competitor").lower()
        probes[key] = await quick_probe(c.url)

    return JSONResponse(synthesize(req.brand, req.competitors, probes))

@app.post("/api/intelligence/export")
async def export_csv(req: AnalyzeRequest):
    probes: Dict[str, Dict[str, Any]] = {}
    probes["brand"] = await quick_probe(req.brand.url)
    for c in req.competitors:
        key = (c.name or _hostish(c.url) or "competitor").lower()
        probes[key] = await quick_probe(c.url)

    data = synthesize(req.brand, req.competitors, probes)

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["brand", "competitor", "signal", "note", "score", "source"])
    for s in data.get("signals", []):
        w.writerow([
            s.get("brand"),
            s.get("competitor") or "",
            s.get("signal"),
            s.get("note"),
            s.get("score"),
            json.dumps(s.get("source") or {}),
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

# Serve hashed assets (e.g., /assets/*.js, *.css) directly
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
    # Let API paths 404 naturally
    if path.startswith("api/"):
        raise HTTPException(404, "Not found")
    p = _index_path()
    if not os.path.isfile(p):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: {p}</p>", status_code=404)
    return FileResponse(p)

# ---------- Debug ----------
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
