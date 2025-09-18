# src/api/main.py
from __future__ import annotations
import os, csv, io, json, re, time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_VERSION = "3.1.0"

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.normpath(os.path.join(HERE, "..", "..", "frontend", "dist"))
FRONTEND_DIST = os.environ.get("WEB_DIR", FRONTEND_DIST)  # optional override with env

app = FastAPI(title="Signal & Scale", version=APP_VERSION, docs_url="/openapi.json", redoc_url=None)

# CORS (relaxed; restrict in prod if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --------- Schemas ---------
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

OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()

def _hostish(s: Optional[str]) -> str:
    if not s: return ""
    s = s.strip()
    if s.startswith("http"):
        h = re.sub(r"^https?://", "", s).split("/")[0].replace("www.", "").split(":")[0]
        return h
    return s

async def quick_probe(url: Optional[str]) -> Dict[str, Any]:
    info = {"reachable": False, "status": None, "shop_pay": False, "apple_pay": False, "klarna": False, "latency_ms": None}
    if not url: return info
    if not url.startswith("http"): url = "https://" + url
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "SignalScale/1.0"})
            info["status"] = r.status_code
            info["reachable"] = 200 <= r.status_code < 400
            txt = (r.text or "")[:100_000].lower()
            info["shop_pay"] = ("shop pay" in txt) or ("shop.app/pay" in txt)
            info["apple_pay"] = ("apple pay" in txt) or ("apple-pay" in txt)
            info["klarna"] = "klarna" in txt
    except Exception:
        pass
    info["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return info

def synthesize(brand: Brand, comps: List[Competitor], probes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    summary = {"brand": brand.name or _hostish(brand.url) or "Brand", "competitors": [c.name or _hostish(c.url) for c in comps]}
    signals: List[Dict[str, Any]] = []
    b = probes.get("brand") or {}
    for c in comps:
        key = (c.name or _hostish(c.url) or "competitor").lower()
        p = probes.get(key) or {}
        # simple deltas
        if p.get("reachable") and not b.get("reachable"):
            signals.append({"brand": summary["brand"], "competitor": c.name or _hostish(c.url),
                            "signal": "Availability gap", "note": "Competitor site reachable while yours timed out. Check uptime/CDN.",
                            "score": 75, "source": {"probe": "reachability"}})
        if (p.get("shop_pay") or p.get("apple_pay") or p.get("klarna")) and not (b.get("shop_pay") or b.get("apple_pay") or b.get("klarna")):
            signals.append({"brand": summary["brand"], "competitor": c.name or _hostish(c.url),
                            "signal": "Checkout trust gap", "note": "Competitor surfaces accelerated pay. Add Shop Pay / Apple Pay / Klarna.",
                            "score": 82, "source": {"probe": "payments"}})
        if isinstance(b.get("latency_ms"), int) and isinstance(p.get("latency_ms"), int) and p["latency_ms"] + 200 < b["latency_ms"]:
            signals.append({"brand": summary["brand"], "competitor": c.name or _hostish(c.url),
                            "signal": "Performance gap", "note": f"Competitor loads faster (~{p['latency_ms']}ms vs {b['latency_ms']}ms). Optimize hero, defer JS.",
                            "score": 72, "source": {"probe": "latency"}})
    if not signals:
        signals.append({"brand": summary["brand"], "competitor": None, "signal": "Baseline",
                        "note": "No obvious deltas from quick probes. Add PDP content audit (video, size charts, UGC).",
                        "score": 50, "source": {"probe": "baseline"}})
    return {"ok": True, "summary": summary, "signals": signals, "probes": probes}

# ---------------- API ----------------
@app.get("/api/health")
async def health():
    return {"ok": True, "service": "signal-scale", "version": APP_VERSION,
            "frontend_dir": FRONTEND_DIST, "frontend_present": os.path.isdir(FRONTEND_DIST)}

@app.post("/api/intelligence/analyze")
async def analyze(req: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None, convert_underscores=False)):
    # Optional API key gate via env API_KEYS="key1,key2"
    allowed = [k.strip() for k in (os.environ.get("API_KEYS") or "").split(",") if k.strip()]
    if allowed and ((x_api_key or "").strip() not in allowed):
        raise HTTPException(401, "Invalid API key")

    probes: Dict[str, Dict[str, Any]] = {}
    probes["brand"] = await quick_probe(req.brand.url)
    for c in req.competitors:
        k = (c.name or _hostish(c.url) or "competitor").lower()
        probes[k] = await quick_probe(c.url)
    return JSONResponse(synthesize(req.brand, req.competitors, probes))

@app.post("/api/intelligence/export")
async def export(req: AnalyzeRequest):
    probes: Dict[str, Dict[str, Any]] = {}
    probes["brand"] = await quick_probe(req.brand.url)
    for c in req.competitors:
        k = (c.name or _hostish(c.url) or "competitor").lower()
        probes[k] = await quick_probe(c.url)
    data = synthesize(req.brand, req.competitors, probes)

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["brand", "competitor", "signal", "note", "score", "source"])
    for s in data.get("signals", []):
        w.writerow([s.get("brand"), s.get("competitor") or "", s.get("signal"), s.get("note"), s.get("score"), json.dumps(s.get("source") or {})])
    bytes_io = io.BytesIO(out.getvalue().encode("utf-8"))
    return StreamingResponse(bytes_io,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="signal_scale_export.csv"'},
    )

# --------------- Serve Frontend ---------------
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
async def spa(path: str):
    # let API routes 404 naturally
    if path.startswith("api/"):
        raise HTTPException(404, "Not found")
    p = _index_path()
    if not os.path.isfile(p):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: {p}</p>", status_code=404)
    return FileResponse(p)

# --------------- Debug ---------------
@app.get("/debug", response_class=PlainTextResponse)
async def debug():
    lines = [f"version={APP_VERSION}", f"FRONTEND_DIST={FRONTEND_DIST}", f"exists={os.path.isdir(FRONTEND_DIST)}"]
    try:
        if os.path.isdir(FRONTEND_DIST):
            files = sorted(os.listdir(FRONTEND_DIST))
            lines.append("files=" + ", ".join(files[:40]))
    except Exception as e:
        lines.append(f"ls_error={e}")
    return "\n".join(lines)
