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
app = FastAPI(title="Signal & Scale", version="2.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # same-origin in Render; permissive is fine here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tiny request log for Render
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

# -------------------- Validation clarity --------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.json()
    except Exception:
        body = "<non-JSON or unreadable>"
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body_received": body})

# -------------------- Provider config --------------------
PROVIDER_ORDER = [p.strip().lower() for p in os.getenv("PROVIDER_ORDER", "manus").split(",") if p.strip()]

# Manus
MANUS_API_KEY   = os.getenv("MANUS_API_KEY", "").strip()
MANUS_BASE_URL  = os.getenv("MANUS_BASE_URL", "").rstrip("/")
MANUS_AGENT_ID  = os.getenv("MANUS_AGENT_ID", "").strip()
MANUS_RUN_PATH  = os.getenv("MANUS_RUN_PATH", "/v1/agents/run")
MANUS_TIMEOUT_S = float(os.getenv("MANUS_TIMEOUT_S", "120"))

# Optional thin-result enrichment (kept off by default)
ENRICH_ON_THIN = os.getenv("ENRICH_ON_THIN", "false").lower() == "true"
THIN_MIN_SIGNALS = int(os.getenv("THIN_MIN_SIGNALS", "2"))

# -------------------- Helpers: brand profiling & synthesis --------------------
ATHLETIC_KEYWORDS = {"nike","adidas","puma","under armour","underarmor","asics","new balance","reebok"}
STREETWEAR_KEYWORDS = {"stüssy","stussy","supreme","kith","palace","huf","pleasures","the hundreds","anti social social club","bape","a bathing ape","crooks","crooks & castles","bbc","ice cream","billionaire boys club","carrots","ksubi","paper planes"}

def _slug(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def infer_category(brand: Brand, comps: List[Competitor]) -> str:
    # Heuristic: look at brand + competitors names
    names = {_slug(brand.name)}
    names.update({_slug(c.name) for c in comps})
    if names & ATHLETIC_KEYWORDS: return "athletic"
    if names & STREETWEAR_KEYWORDS: return "streetwear"
    # Fallback by URL hints
    url = _slug(brand.url)
    if any(k in url for k in ["run","sport","athlet"]): return "athletic"
    return "apparel_lifestyle"

def audience_archetypes(category: str) -> List[str]:
    if category == "athletic":
        return ["performance athletes","runners & trainers","sports fandom micro-creators","fitness TikTok (how-to)"]
    if category == "streetwear":
        return ["fashion micro-creators (fit checks)","sneakerhead culture","music-adjacent tastemakers","archival/vintage curators"]
    return ["lifestyle fashion shoppers","micro UGC reviewers","deal-hunters","college fashion creators"]

def creator_playbook(category: str) -> List[Dict[str, Any]]:
    if category == "athletic":
        return [
            {"type":"coach/athlete micro","why":"authentic performance proof","activation":"seed + test workouts"},
            {"type":"running TikTok","why":"high tutorial consumption","activation":"UGC briefs (30s drills)"},
            {"type":"team fandom","why":"tribal share loops","activation":"city/team capsules"}
        ]
    if category == "streetwear":
        return [
            {"type":"fit-check micro","why":"contextual styling boosts intent","activation":"styling challenges + affiliate"},
            {"type":"sneakerhead","why":"release cycles drive spikes","activation":"co-drop hooks + early pairs"},
            {"type":"archival curators","why":"heritage storytelling","activation":"archive-to-modern remix series"}
        ]
    return [
        {"type":"UGC reviewers","why":"social proof for DTC","activation":"rapid A/B UGC hooks"},
        {"type":"campus creators","why":"peer-led discovery","activation":"ambassador kits"}
    ]

def competitor_focus_points(category: str) -> List[str]:
    if category == "athletic":
        return ["performance messaging","size/fit assurance","bundle offers","retail distribution w/ sports specialty"]
    if category == "streetwear":
        return ["drop cadence & storytelling","PDP media richness","collab pages & editorial","community/UGC integration"]
    return ["value clarity & entry pricing","PDP trust (reviews, size charts)","checkout speed (express pays)"]

def synthesize_brand_strategy(brand: Brand, comps: List[Competitor], manus_sections: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn Manus structured sections into brand-specific, category-aware actions."""
    cat = infer_category(brand, comps)
    archetypes = audience_archetypes(cat)
    creators = creator_playbook(cat)
    comp_focus = competitor_focus_points(cat)

    signals: List[Dict[str, Any]] = []

    # Weekly report → actionable moves
    wr = manus_sections.get("weekly_report") or {}
    for opp in wr.get("opportunities_risks", [])[:8]:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"[{cat}] {opp.get('type','opportunity').title()}: {opp.get('insight','')}",
            "score": {"high": 85, "medium": 65, "low": 45}.get((opp.get("impact") or "medium").lower(), 60),
            "note": "source: manus | section: weekly_report"
        })

    # Cultural radar → top creators
    cr = manus_sections.get("cultural_radar") or {}
    for c in (cr.get("creators") or [])[:10]:
        label = "Tier1" if c.get("crooks_mentioned") else "Prospect"
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"Creator {label}: {c.get('creator','')} on {c.get('platform','')}",
            "score": int(round((c.get("influence_score") or 0))),
            "note": f"source: manus | section: cultural_radar | rec: {c.get('recommendation','')}"
        })

    # Peer tracker → gaps per competitor
    pt = manus_sections.get("peer_tracker") or {}
    sc = (pt.get("scorecard") or {}).get("scores") or []
    # Focus on category-relevant dimensions
    wanted_dims = {
        "athletic": {"PDP","Checkout","PricePresentation"},
        "streetwear": {"Homepage","ContentCommunity","PDP"},
        "apparel_lifestyle": {"PDP","Checkout","MobileUX"}
    }[cat]
    # Build quick “where we’re behind” prompts
    crooks = [s for s in sc if (s.get("brand") or "").lower().startswith("crooks")]
    for c in comps[:8]:
        cname = c.name or ""
        peer_rows = [s for s in sc if (s.get("brand") or "").lower().startswith(_slug(cname))]
        for dim in wanted_dims:
            cs = next((s for s in crooks if s.get("dimension")==dim), None)
            ps = next((s for s in peer_rows if s.get("dimension")==dim), None)
            if cs and ps and isinstance(cs.get("score"), (int, float)) and isinstance(ps.get("score"), (int, float)):
                delta = float(ps["score"]) - float(cs["score"])
                if delta > 0.5:
                    signals.append({
                        "brand": brand.name or "Unknown",
                        "competitor": cname,
                        "signal": f"Close gap on {dim}: {cname} +{delta:.1f}",
                        "score": 70 if dim in ("PDP","Checkout") else 60,
                        "note": f"source: manus | section: peer_tracker | notes: {', '.join((ps.get('notes') or [])[:2])}"
                    })

    # Category archetypes → proactive moves (always brand-specific due to category)
    for a in archetypes:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"Audience to activate: {a}",
            "score": 55,
            "note": f"source: strategy | category: {cat}"
        })
    for cp in creators:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"Creator play: {cp['type']} — {cp['activation']}",
            "score": 58,
            "note": f"why: {cp['why']} | category: {cat} | source: strategy"
        })
    for f in comp_focus:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"Competitor focus area: {f}",
            "score": 57,
            "note": f"category: {cat} | source: strategy"
        })
    return signals

# -------------------- Normalizers --------------------
def normalize_from_manus(brand: Brand, comps: List[Competitor], raw: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Expects the structured JSON sections from your Manus agent:
    { weekly_report: {...}, cultural_radar: {...}, peer_tracker: {...}, warnings?:[] }
    Produces flattened signals + returns sections for the strategy synthesizer.
    """
    sections = {
        "weekly_report": raw.get("weekly_report") or {},
        "cultural_radar": raw.get("cultural_radar") or {},
        "peer_tracker": raw.get("peer_tracker") or {},
        "warnings": raw.get("warnings") or []
    }
    signals: List[Dict[str, Any]] = []

    # Weekly: highlights + opportunities become signals
    for hl in (sections["weekly_report"].get("engagement_highlights") or [])[:10]:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"Engagement highlight: {hl.get('why_it_matters','')}",
            "score": 65,
            "note": f"source: manus | section: weekly_report | link: {hl.get('link','')}"
        })
    for opp in (sections["weekly_report"].get("opportunities_risks") or [])[:10]:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"{opp.get('type','opportunity').title()}: {opp.get('insight','')}",
            "score": {"high":85,"medium":65,"low":45}.get((opp.get("impact") or "medium").lower(), 60),
            "note": "source: manus | section: weekly_report"
        })
    # Cultural radar: include top 5
    for c in (sections["cultural_radar"].get("creators") or [])[:5]:
        signals.append({
            "brand": brand.name or "Unknown",
            "competitor": "",
            "signal": f"Creator: {c.get('creator','')} ({c.get('platform','')})",
            "score": int(round((c.get("influence_score") or 0))),
            "note": f"source: manus | section: cultural_radar | profile: {c.get('profile','')}"
        })
    # Peer tracker: include deltas against Crooks if present
    sc = (sections["peer_tracker"].get("scorecard") or {}).get("scores") or []
    crooks = [s for s in sc if (s.get("brand") or "").lower().startswith("crooks")]
    for c in comps[:8]:
        cname = c.name or ""
        peer_rows = [s for s in sc if (s.get("brand") or "").lower().startswith(_slug(cname))]
        for dim in {"Homepage","PDP","Checkout","ContentCommunity","MobileUX","PricePresentation"}:
            cs = next((s for s in crooks if s.get("dimension")==dim), None)
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
                        "note": f"source: manus | section: peer_tracker"
                    })
    return signals, sections

def is_thin(rows: List[Dict[str, Any]]) -> bool:
    if not rows: return True
    meaningful = [r for r in rows if (r.get("signal") or "").lower() not in ("", "no insights")]
    return len(meaningful) < THIN_MIN_SIGNALS

def fallback_rows(brand: Brand, comps: List[Competitor], note: str) -> List[Dict[str, Any]]:
    b = (brand.name or "").strip() or "Unknown Brand"
    if not comps:
        return [{"brand": b, "competitor":"", "signal":"Add competitors for better differentiation", "score":0, "note": f"source: fallback ({note})"}]
    out=[]
    cat = infer_category(brand, comps)
    for c in comps:
        out.append({"brand": b, "competitor": c.name or "Unnamed", "signal": f"Baseline comparison — category {cat}", "score": 50, "note": f"source: fallback ({note})"})
    # add category-specific suggestions so Nike vs Crooks diverge
    for s in synthesize_brand_strategy(brand, comps, {"weekly_report":{}, "cultural_radar":{}, "peer_tracker":{}})[:6]:
        s["note"] = s.get("note","") + " | fallback"
        out.append(s)
    return out

# -------------------- Manus provider --------------------
def call_manus(req: AnalyzeRequest) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not (MANUS_API_KEY and MANUS_BASE_URL and MANUS_AGENT_ID):
        raise RuntimeError("Manus not configured")

    payload = {
        "agent_id": MANUS_AGENT_ID,
        "brand": req.brand.dict(),
        "competitors": [c.dict() for c in req.competitors],
        "mode": req.mode or "all",
        "window_days": req.window_days or 7,
        # Optional knobs can be forwarded if set in req.brand.meta etc.
        "context": {"source":"signal-scale","version":"2.4.0"}
    }
    headers = {"Authorization": f"Bearer {MANUS_API_KEY}", "Content-Type": "application/json"}
    url = f"{MANUS_BASE_URL}{MANUS_RUN_PATH}"

    with httpx.Client(timeout=MANUS_TIMEOUT_S) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw": r.text}

    rows, sections = normalize_from_manus(req.brand, req.competitors, data)
    # Optional enrichment on thin results (kept internal, still brand-differentiated via category)
    if ENRICH_ON_THIN and is_thin(rows):
        rows += synthesize_brand_strategy(req.brand, req.competitors, sections)[:10]
    return rows, sections

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
        except Exception as e:
            errors.append(f"manus: {type(e).__name__}: {str(e)[:200]}")
            continue

    if not rows:
        note = " | ".join(errors) if errors else "no provider configured"
        rows = fallback_rows(req.brand, req.competitors, note=note)
        sections = {"weekly_report":{}, "cultural_radar":{}, "peer_tracker":{}, "warnings":[note]}

    # Always add strategy synthesis on top of base rows for differentiation
    # (if Manus already provided rich sections, this adds category-aware actions)
    strategy_signals = synthesize_brand_strategy(req.brand, req.competitors, sections)[:12]
    # Deduplicate (competitor, signal) pairs
    seen = set()
    final_rows: List[Dict[str, Any]] = []
    for r in rows + strategy_signals:
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
        "sections": sections  # keep raw Manus sections for future UI
    }

# -------------------- API --------------------
@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": "2.4.0",
        "keys_enabled": bool(APP_API_KEYS),
        "manus_configured": bool(MANUS_API_KEY),
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
INDEX_HTML = os.path.join(WEB_DIR, "index.html")

print(f"[startup] WEB_DIR={WEB_DIR} exists={os.path.isdir(WEB_DIR)}", file=sys.stdout, flush=True)
print(f"[startup] INDEX_HTML exists={os.path.exists(INDEX_HTML)}", file=sys.stdout, flush=True)

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