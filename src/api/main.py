# main.py — Signal & Scale API (v2.5.1)
# Dependencies: fastapi, uvicorn[standard], httpx, pydantic

import os, io, csv, json, sys
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# -------------------- App --------------------
app = FastAPI(title="Signal & Scale", version="2.5.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    resp = await call_next(request)
    print(f"{request.method} {request.url.path} -> {resp.status_code}", flush=True)
    return resp

# -------------------- Auth (your customers’ keys) --------------------
def _load_keys(env_name: str) -> List[str]:
    raw = os.getenv(env_name, "").strip()
    if not raw: return []
    return [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]

APP_API_KEYS = _load_keys("API_KEYS")  # e.g., "sk_live_demo,sk_client_A"

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
    mode: Optional[str] = "all"      # weekly_report | cultural_radar | peer_tracker | all
    window_days: Optional[int] = 7
    class Config: extra = "ignore"

# Clear 422s with body echo
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.json()
    except Exception:
        body = "<non-JSON or unreadable>"
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body_received": body})

# -------------------- Provider config --------------------
PROVIDER_ORDER = [p.strip().lower() for p in os.getenv("PROVIDER_ORDER", "manus,openai").split(",") if p.strip()]

# Manus
MANUS_API_KEY   = os.getenv("MANUS_API_KEY", "").strip()
MANUS_BASE_URL  = os.getenv("MANUS_BASE_URL", "").rstrip("/")
MANUS_AGENT_ID  = os.getenv("MANUS_AGENT_ID", "").strip()
MANUS_RUN_PATH  = os.getenv("MANUS_RUN_PATH", "/v1/agents/run")
MANUS_TIMEOUT_S = float(os.getenv("MANUS_TIMEOUT_S", "120"))

# OpenAI (optional)
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_CHAT_URL  = os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions").strip()
OPENAI_TIMEOUT_S = float(os.getenv("OPENAI_TIMEOUT_S", "60"))

# Thin-result enrichment (optional)
ENRICH_ON_THIN   = os.getenv("ENRICH_ON_THIN", "false").lower() == "true"
THIN_MIN_SIGNALS = int(os.getenv("THIN_MIN_SIGNALS", "2"))

# -------------------- Category heuristics (for differentiation) --------------------
ATHLETIC_KEYWORDS = {"nike","adidas","puma","under armour","underarmor","asics","new balance","reebok"}
STREETWEAR_KEYWORDS = {"stüssy","stussy","supreme","kith","palace","huf","pleasures","the hundreds","anti social social club","bape","a bathing ape","crooks","crooks & castles","bbc","ice cream","billionaire boys club","carrots","ksubi","paper planes"}

def _slug(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def infer_category(brand: Brand, comps: List[Competitor]) -> str:
    names = {_slug(brand.name)} | {_slug(c.name) for c in comps}
    if names & ATHLETIC_KEYWORDS: return "athletic"
    if names & STREETWEAR_KEYWORDS: return "streetwear"
    url = _slug(brand.url)
    if any(k in url for k in ["run","sport","athlet"]): return "athletic"
    return "apparel_lifestyle"

def audience_archetypes(category: str) -> List[str]:
    if category == "athletic":
        return ["performance athletes","runners & trainers","sports-fandom micro-creators","fitness how-to TikTok"]
    if category == "streetwear":
        return ["fit-check micros","sneakerhead culture","music-adjacent tastemakers","archival/vintage curators"]
    return ["lifestyle fashion shoppers","UGC reviewers","deal-hunters","campus creators"]

def creator_playbook(category: str) -> List[Dict[str, Any]]:
    if category == "athletic":
        return [
            {"type":"coach/athlete micro","why":"performance proof","activation":"seed + test workouts"},
            {"type":"running TikTok","why":"tutorial demand","activation":"UGC briefs (30s drills)"},
            {"type":"team fandom","why":"tribal loops","activation":"city/team capsules"},
        ]
    if category == "streetwear":
        return [
            {"type":"fit-check micro","why":"contextual styling","activation":"styling challenges + affiliate"},
            {"type":"sneakerhead","why":"release cycles","activation":"co-drop hooks + early pairs"},
            {"type":"archival curator","why":"heritage storytelling","activation":"archive→modern remix"},
        ]
    return [
        {"type":"UGC reviewers","why":"social proof","activation":"rapid A/B hooks"},
        {"type":"campus creators","why":"peer discovery","activation":"ambassador kits"},
    ]

def competitor_focus_points(category: str) -> List[str]:
    if category == "athletic":
        return ["performance messaging","size/fit assurance","bundles","sports specialty distribution"]
    if category == "streetwear":
        return ["drop cadence/story","PDP media richness","collab/editorial hubs","community/UGC"]
    return ["value clarity/entry price","PDP trust (reviews/size)","checkout speed (express pays)"]

# -------------------- Normalization & synthesis --------------------
def normalize_from_manus(brand: Brand, comps: List[Competitor], raw: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Expect Manus to return structured JSON sections (weekly_report, cultural_radar, peer_tracker)."""
    sections = {
        "weekly_report": raw.get("weekly_report") or {},
        "cultural_radar": raw.get("cultural_radar") or {},
        "peer_tracker": raw.get("peer_tracker") or {},
        "warnings": raw.get("warnings") or []
    }
    signals: List[Dict[str, Any]] = []

    # Weekly highlights + opportunities
    for hl in (sections["weekly_report"].get("engagement_highlights") or [])[:10]:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"Engagement highlight: {hl.get('why_it_matters','')}",
            "score": 65,
            "note": f"source: manus | section: weekly_report | link: {hl.get('link','')}"
        })
    for opp in (sections["weekly_report"].get("opportunities_risks") or [])[:10]:
        impact = (opp.get("impact") or "medium").lower()
        score = {"high":85,"medium":65,"low":45}.get(impact, 60)
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"{opp.get('type','opportunity').title()}: {opp.get('insight','')}",
            "score": score,
            "note": "source: manus | section: weekly_report"
        })

    # Cultural radar: top creators
    for c in (sections["cultural_radar"].get("creators") or [])[:5]:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"Creator: {c.get('creator','')} ({c.get('platform','')})",
            "score": int(round((c.get("influence_score") or 0))),
            "note": f"source: manus | section: cultural_radar | profile: {c.get('profile','')}"
        })

    # Peer tracker: compare focal brand vs peers by dimension
    sc = (sections["peer_tracker"].get("scorecard") or {}).get("scores") or []
    focal = [s for s in sc if _slug(s.get("brand")) == _slug(brand.name)]
    for c in comps[:8]:
        cname = c.name or ""
        peer_rows = [s for s in sc if _slug(s.get("brand")) == _slug(cname)]
        for dim in {"Homepage","PDP","Checkout","ContentCommunity","MobileUX","PricePresentation"}:
            cs = next((s for s in focal if s.get("dimension")==dim), None)
            ps = next((s for s in peer_rows if s.get("dimension")==dim), None)
            if cs and ps and isinstance(cs.get("score"), (int,float)) and isinstance(ps.get("score"), (int,float)):
                delta = float(ps["score"]) - float(cs["score"])
                if abs(delta) >= 1.0:
                    tag = "Behind" if delta>0 else "Ahead"
                    signals.append({
                        "brand": brand.name or "Unknown",
                        "competitor": cname,
                        "signal": f"{tag} on {dim} by {abs(delta):.1f}",
                        "score": 60,
                        "note": "source: manus | section: peer_tracker"
                    })
    return signals, sections

def synthesize_brand_strategy(brand: Brand, comps: List[Competitor], sections: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Category-aware actions so Nike ≠ Crooks ≠ Boutique."""
    cat = infer_category(brand, comps)
    signals: List[Dict[str, Any]] = []

    # Audience archetypes & creator plays
    for a in audience_archetypes(cat):
        signals.append({"brand": brand.name or "Unknown", "competitor":"", "signal": f"Audience to activate: {a}", "score":55, "note": f"source: strategy | category: {cat}"})
    for cp in creator_playbook(cat):
        signals.append({"brand": brand.name or "Unknown", "competitor":"", "signal": f"Creator play: {cp['type']} — {cp['activation']}", "score":58, "note": f"why: {cp['why']} | category: {cat} | source: strategy"})
    for f in competitor_focus_points(cat):
        signals.append({"brand": brand.name or "Unknown", "competitor":"", "signal": f"Competitor focus area: {f}", "score":57, "note": f"category: {cat} | source: strategy"})

    # Surface top Manus opportunities again as explicit actions
    for opp in (sections.get("weekly_report", {}).get("opportunities_risks") or [])[:5]:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor":"",
            "signal": f"[{cat}] {opp.get('type','opportunity').title()}: {opp.get('insight','')}",
            "score": {"high":85,"medium":65,"low":45}.get((opp.get("impact") or "medium").lower(), 60),
            "note":"source: manus | section: weekly_report"
        })
    return signals

def is_thin(rows: List[Dict[str, Any]]) -> bool:
    if not rows: return True
    meaningful = [r for r in rows if (r.get("signal") or "").strip().lower() not in ("", "no insights")]
    return len(meaningful) < THIN_MIN_SIGNALS

def fallback_rows(brand: Brand, comps: List[Competitor], note: str) -> List[Dict[str, Any]]:
    b = (brand.name or "").strip() or "Unknown Brand"
    out: List[Dict[str, Any]] = []
    cat = infer_category(brand, comps)
    if not comps:
        out.append({"brand": b, "competitor":"", "signal":"Add competitors for better differentiation", "score":0, "note": f"source: fallback ({note})"})
    else:
        for c in comps:
            out.append({"brand": b, "competitor": c.name or "Unnamed", "signal": f"Baseline comparison — category {cat}", "score": 50, "note": f"source: fallback ({note})"})
    out += [dict(s, note=(s.get("note","") + " | fallback")) for s in synthesize_brand_strategy(brand, comps, {"weekly_report":{}})[:6]]
    return out

# -------------------- Providers --------------------
def call_manus(req: AnalyzeRequest) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not (MANUS_API_KEY and MANUS_BASE_URL and MANUS_AGENT_ID):
        raise RuntimeError("Manus not configured")
    payload = {
        "agent_id": MANUS_AGENT_ID,
        "brand": req.brand.dict(),
        "competitors": [c.dict() for c in req.competitors],
        "mode": req.mode or "all",
        "window_days": req.window_days or 7,
        "context": {"source":"signal-scale","version":"2.5.1"}
    }
    headers = {"Authorization": f"Bearer {MANUS_API_KEY}", "Content-Type": "application/json"}
    url = f"{MANUS_BASE_URL}{MANUS_RUN_PATH}"
    with httpx.Client(timeout=MANUS_TIMEOUT_S) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw": r.text}
    rows, sections = normalize_from_manus(req.brand, req.competitors, data)
    if ENRICH_ON_THIN and is_thin(rows):
        rows += synthesize_brand_strategy(req.brand, req.competitors, sections)[:10]
    return rows, sections

def call_openai(req: AnalyzeRequest) -> List[Dict[str, Any]]:
    """Simple brand-differentiated fallback using OpenAI Chat Completions."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI not configured")
    category = infer_category(req.brand, req.competitors)
    sys_msg = {
        "role": "system",
        "content": (
            "You are a competitive intelligence analyst. Return STRICT JSON only with shape: "
            '{"insights":[{"competitor":"","title":"","score":0,"note":""}]}. '
            "Differentiate by brand category and competitor context. No markdown, no prose."
        )
    }
    user_payload = {
        "brand": req.brand.dict(),
        "competitors": [c.dict() for c in req.competitors],
        "category_hint": category
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {"model": OPENAI_MODEL, "messages": [sys_msg, {"role": "user", "content": json.dumps(user_payload)}], "temperature": 0.2}
    with httpx.Client(timeout=OPENAI_TIMEOUT_S) as client:
        r = client.post(OPENAI_CHAT_URL, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or "{}"
    # Parse safely
    out: List[Dict[str, Any]] = []
    try:
        parsed = json.loads(text)
        for it in (parsed.get("insights") or []):
            out.append({
                "brand": req.brand.name or "Unknown",
                "competitor": it.get("competitor",""),
                "signal": it.get("title",""),
                "score": int(it.get("score", 0)) if isinstance(it.get("score", 0), (int,float)) else 0,
                "note": f"source: openai | {it.get('note','')}"
            })
    except Exception:
        # if the model returned non-JSON, produce a single generic but category-aware row
        out.append({
            "brand": req.brand.name or "Unknown",
            "competitor": "",
            "signal": f"Category-driven next move ({category})",
            "score": 55,
            "note": "source: openai | parse_fallback"
        })
    return out

# -------------------- Core --------------------
def analyze_core(req: AnalyzeRequest) -> Dict[str, Any]:
    errors: List[str] = []
    rows: List[Dict[str, Any]] = []
    sections: Dict[str, Any] = {}

    for p in PROVIDER_ORDER:
        try:
            if p == "manus":
                rows, sections = call_manus(req)
                if rows: break
            elif p == "openai":
                rows = call_openai(req)
                if rows: break
        except Exception as e:
            errors.append(f"{p}: {type(e).__name__}: {str(e)[:200]}")
            continue

    if not rows:
        note = " | ".join(errors) if errors else "no provider configured"
        rows = fallback_rows(req.brand, req.competitors, note=note)
        sections = {"weekly_report":{}, "cultural_radar":{}, "peer_tracker":{}, "warnings":[note]}

    # Always add small category-aware strategy set for differentiation
    strategy = synthesize_brand_strategy(req.brand, req.competitors, sections)[:12]
    # Deduplicate (competitor, signal)
    seen = set()
    final_rows: List[Dict[str, Any]] = []
    for r in rows + strategy:
        key = (_slug(r.get("competitor")), _slug(r.get("signal")))
        if key in seen: continue
        seen.add(key)
        final_rows.append(r)

    return {
        "ok": True,
        "brand": req.brand.dict(),
        "competitors_count": len(req.competitors),
        "category_inferred": infer_category(req.brand, req.competitors),
        "signals": final_rows,
        "sections": sections
    }

# -------------------- API --------------------
@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": "2.5.1",
        "keys_enabled": bool(APP_API_KEYS),
        "manus_configured": bool(MANUS_API_KEY),
        "openai_configured": bool(OPENAI_API_KEY),
        "provider_order": PROVIDER_ORDER
    }

@app.get("/api/integrations/manus/check")
def manus_check(_=Depends(require_api_key)):
    return {
        "configured": bool(MANUS_API_KEY),
        "base_url_set": bool(MANUS_BASE_URL),
        "agent_id_set": bool(MANUS_AGENT_ID),
        "run_path": MANUS_RUN_PATH,
        "timeout_s": MANUS_TIMEOUT_S
    }

@app.get("/api/integrations/openai/check")
def openai_check(_=Depends(require_api_key)):
    return {
        "configured": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL,
        "chat_url": OPENAI_CHAT_URL
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
        headers={"Content-Disposition": 'attachment; filename=\"signal_scale_export.csv\"'}
    )

# -------------------- Frontend (serve / + /static) --------------------
def find_web_dir() -> str:
    override = os.getenv("WEB_DIR", "").strip()
    if override and os.path.exists(os.path.join(override, "index.html")):
        return override
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "web"),                 # src/api/web
        os.path.join(base_dir, "..", "web"),           # src/web
        os.path.join(base_dir, "..", "..", "web"),     # web at repo root
        os.path.join(os.getcwd(), "web"),              # CWD/web
    ]
    for c in map(os.path.abspath, candidates):
        if os.path.exists(os.path.join(c, "index.html")):
            return c
    return os.path.abspath(os.path.join(base_dir, "web"))

WEB_DIR = find_web_dir()
INDEX_HTML = os.path.join(WEB_DIR, "index.html")

print(f"[startup] USING WEB_DIR={WEB_DIR} exists={os.path.isdir(WEB_DIR)}", flush=True)
print(f"[startup] INDEX_HTML exists={os.path.exists(INDEX_HTML)}", flush=True)

if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def root():
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def spa_fallback(full_path: str):
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not found")
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

@app.api_route("/favicon.ico", methods=["GET", "HEAD"])
def favicon():
    ico_path = os.path.join(WEB_DIR, "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path)
    return HTMLResponse("", status_code=204)