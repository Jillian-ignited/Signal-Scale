import os, io, csv, json, sys
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# -------------------- App --------------------
app = FastAPI(title="Signal & Scale", version="2.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # same-origin in prod; permissive is fine here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple request logging (shows method/path/status in Render logs)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    resp = await call_next(request)
    print(f"{request.method} {request.url.path} -> {resp.status_code}", flush=True)
    return resp

# -------------------- Auth (API keys you issue to customers) --------------------
def _load_keys(env_name: str) -> List[str]:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]

APP_API_KEYS = _load_keys("API_KEYS")  # e.g., "sk_live_demo,sk_live_clientA"

def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if APP_API_KEYS and (x_api_key not in APP_API_KEYS):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key

# -------------------- Models --------------------
class Brand(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    class Config: extra = "ignore"

class Competitor(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    class Config: extra = "ignore"

class AnalyzeRequest(BaseModel):
    brand: Brand = Field(default_factory=Brand)
    competitors: List[Competitor] = Field(default_factory=list)
    class Config: extra = "ignore"

# -------------------- Error clarity --------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.json()
    except Exception:
        body = "<non-JSON or unreadable>"
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body_received": body})

# -------------------- Optional Manus integration --------------------
MANUS_API_KEY   = os.getenv("MANUS_API_KEY", "").strip()
MANUS_BASE_URL  = os.getenv("MANUS_BASE_URL", "").rstrip("/")   # e.g., https://api.manus.im
MANUS_AGENT_ID  = os.getenv("MANUS_AGENT_ID", "").strip()
MANUS_RUN_PATH  = os.getenv("MANUS_RUN_PATH", "/v1/agents/run")
MANUS_TIMEOUT_S = float(os.getenv("MANUS_TIMEOUT_S", "120"))

def _fallback_rows(brand: Brand, comps: List[Competitor]) -> List[Dict[str, Any]]:
    b = (brand.name or "").strip() or "Unknown Brand"
    if not comps:
        return [{"brand": b, "competitor":"", "signal":"No competitors submitted", "score":0, "note":"Add competitors."}]
    rows = []
    for c in comps:
        cname = (c.name or "").strip() or "Unnamed Competitor"
        rows.append({"brand": b, "competitor": cname, "signal":"Baseline comparison (fallback)", "score":50, "note":"source: fallback"})
    return rows

def _normalize_manus(brand: Brand, comps: List[Competitor], raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    b = (brand.name or "").strip() or "Unknown Brand"
    rows: List[Dict[str, Any]] = []
    results = (raw or {}).get("results", [])
    if not isinstance(results, list):
        results = []
    for item in results:
        cname = item.get("competitor") or "Unnamed Competitor"
        insights = item.get("insights") or []
        if not insights:
            rows.append({"brand": b, "competitor": cname, "signal":"No insights", "score":"", "note":"source: manus"})
        for ins in insights:
            rows.append({
                "brand": b, "competitor": cname,
                "signal": ins.get("title") or ins.get("summary") or "Insight",
                "score": ins.get("score",""),
                "note": (ins.get("note","") + " | source: manus").strip(" |")
            })
    if not rows and raw:
        rows.append({"brand": b, "competitor":"", "signal":"Unparsed Manus payload", "score":"", "note": json.dumps(raw)[:2000]})
    return rows

def call_manus(brand: Brand, comps: List[Competitor]) -> List[Dict[str, Any]]:
    if MANUS_API_KEY and MANUS_BASE_URL and MANUS_AGENT_ID:
        try:
            payload = {
                "agent_id": MANUS_AGENT_ID,
                "brand": brand.dict(),
                "competitors": [c.dict() for c in comps],
                "context": {"source":"signal-scale","version":"2.2.0"}
            }
            headers = {"Authorization": f"Bearer {MANUS_API_KEY}", "Content-Type":"application/json"}
            url = f"{MANUS_BASE_URL}{MANUS_RUN_PATH}"
            with httpx.Client(timeout=MANUS_TIMEOUT_S) as client:
                r = client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw": r.text}
            return _normalize_manus(brand, comps, data)
        except Exception as e:
            b = (brand.name or "").strip() or "Unknown Brand"
            return [{"brand": b, "competitor":"", "signal":"Manus call failed; using fallback", "score":"", "note": f"{type(e).__name__}: {str(e)[:300]}"}]
    return _fallback_rows(brand, comps)

def analyze_core(req: AnalyzeRequest) -> Dict[str, Any]:
    rows = call_manus(req.brand, req.competitors)
    return {"ok": True, "brand": req.brand.dict(), "competitors_count": len(req.competitors), "signals": rows}

# -------------------- API --------------------
@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": "2.2.0",
        "keys_enabled": bool(APP_API_KEYS),
        "manus_configured": bool(MANUS_API_KEY)
    }

@app.get("/api/intelligence/schema")
def schema():
    return {"expected": {"brand":{"name":"string","url":"string","meta?":"object"},"competitors":"array of {name,url,meta?}"}}

@app.get("/api/integrations/manus/check")
def manus_check(_=Depends(require_api_key)):
    return {
        "configured": bool(MANUS_API_KEY),
        "base_url_set": bool(MANUS_BASE_URL),
        "agent_id_set": bool(MANUS_AGENT_ID),
        "timeout_s": MANUS_TIMEOUT_S
    }

@app.post("/api/intelligence/analyze")
def analyze(req: AnalyzeRequest, _=Depends(require_api_key)):
    return analyze_core(req)

@app.post("/api/intelligence/export")
def export_csv(req: AnalyzeRequest, _=Depends(require_api_key)):
    result = analyze_core(req)
    rows = result.get("signals", [])
    buf = io.StringIO()
    fieldnames = ["brand","competitor","signal","score","note"]
    w = csv.DictWriter(buf, fieldnames=fieldnames); w.writeheader()
    for r in rows: w.writerow({k: r.get(k,"") for k in fieldnames})
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="signal_scale_export.csv"'}
    )

# -------------------- Frontend: serve from /static + explicit "/" --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
INDEX_HTML = os.path.join(WEB_DIR, "index.html")

print(f"[startup] WEB_DIR={WEB_DIR} exists={os.path.isdir(WEB_DIR)}", file=sys.stdout, flush=True)
print(f"[startup] INDEX_HTML exists={os.path.exists(INDEX_HTML)}", file=sys.stdout, flush=True)

# Serve static assets (e.g., /static/main.js)
if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# HEAD and GET both supported at root to prevent 405s
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def root():
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

# SPA fallback: any non-API path returns index.html (GET/HEAD)
@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def spa_fallback(full_path: str):
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not found")
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

# Optional: quiet 204 for favicon
@app.api_route("/favicon.ico", methods=["GET", "HEAD"])
def favicon():
    ico_path = os.path.join(WEB_DIR, "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path)
    return HTMLResponse("", status_code=204)
