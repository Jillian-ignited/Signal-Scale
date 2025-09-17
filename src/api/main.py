# src/api/main.py  — Signal & Scale (clean, no-Manus) v3.1
# Minimal deps: fastapi, uvicorn[standard], httpx, pydantic

import os, io, csv, json, re
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

# ---------------- App & CORS ----------------
API_PREFIX = os.getenv("API_PREFIX", "/api").rstrip("/")
app = FastAPI(title="Signal & Scale", version="3.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.middleware("http")
async def _log(req, call_next):
    resp = await call_next(req)
    print(f"{req.method} {req.url.path} -> {resp.status_code}", flush=True)
    return resp

# ------------- Auth (optional) -------------
def _load_keys(env_name: str) -> List[str]:
    raw = os.getenv(env_name, "").strip()
    if not raw: return []
    return [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]

APP_API_KEYS = _load_keys("API_KEYS")  # e.g. "sk_live_demo,sk_client_a"

def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if APP_API_KEYS and (x_api_key not in APP_API_KEYS):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key

# ------------- Models ----------------------
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
    mode: Optional[str] = "all"
    window_days: Optional[int] = 7
    # Optional: pasted text reports (lets you operate without external agents)
    reports: List[str] = Field(default_factory=list)
    class Config: extra = "ignore"

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    body = "<unreadable>"
    try:
        body = await request.body()
        body = body.decode("utf-8", errors="ignore")
    except Exception:
        pass
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body_received": body})

# ------------- Provider config (OpenAI optional) -------------
PROVIDER_ORDER = [p.strip().lower() for p in os.getenv("PROVIDER_ORDER", "openai").split(",") if p.strip()]
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_CHAT_URL  = os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions").strip()
OPENAI_TIMEOUT_S = float(os.getenv("OPENAI_TIMEOUT_S", "45"))
ENRICH_ON_THIN   = os.getenv("ENRICH_ON_THIN", "true").lower() == "true"
THIN_MIN_SIGNALS = int(os.getenv("THIN_MIN_SIGNALS", "2"))

# ------------- Simple category heuristics --------------------
ATHLETIC = {"nike","adidas","puma","under armour","underarmor","asics","new balance","reebok"}
STREET   = {"stüssy","stussy","supreme","kith","palace","huf","pleasures","the hundreds","bape","a bathing ape","crooks","crooks & castles","bbc","ice cream","billionaire boys club","carrots","ksubi","paper planes"}

def _slug(s: Optional[str]) -> str: return (s or "").strip().lower()

def infer_category(brand: Brand, comps: List[Competitor]) -> str:
    names = {_slug(brand.name)} | {_slug(c.name) for c in comps}
    if names & ATHLETIC: return "athletic"
    if names & STREET:   return "streetwear"
    url = _slug(brand.url)
    if any(k in url for k in ["run","sport","athlet"]): return "athletic"
    return "apparel_lifestyle"

def audience_archetypes(cat: str) -> List[str]:
    if cat == "athletic":
        return ["runners/trainers","performance athletes","fitness how-to TikTok","sports-fandom micros"]
    if cat == "streetwear":
        return ["fit-check micros","sneakerhead culture","music-adjacent tastemakers","archive/vintage curators"]
    return ["lifestyle fashion shoppers","UGC reviewers","deal hunters","campus creators"]

def creator_playbook(cat: str) -> List[Dict[str, Any]]:
    if cat == "athletic":
        return [
            {"type":"coach/athlete micro","why":"performance proof","activation":"seed + workout formats"},
            {"type":"running TikTok","why":"tutorial demand","activation":"short drills UGC"},
            {"type":"team fandom","why":"tribal loops","activation":"city/team capsules"},
        ]
    if cat == "streetwear":
        return [
            {"type":"fit-check micro","why":"context styling","activation":"styling challenge + affiliate"},
            {"type":"sneakerhead","why":"release cycles","activation":"co-drop hooks + early pairs"},
            {"type":"archival curator","why":"heritage story","activation":"archive→modern remix"},
        ]
    return [
        {"type":"UGC reviewers","why":"social proof","activation":"rapid AB hooks"},
        {"type":"campus creators","why":"peer discovery","activation":"ambassador kits"},
    ]

def competitor_focus_points(cat: str) -> List[str]:
    if cat == "athletic":  return ["performance messaging","fit assurance","bundles","sports specialty distribution"]
    if cat == "streetwear":return ["drop cadence/story","PDP media richness","collab/editorial hubs","community/UGC"]
    return ["value clarity/entry price","PDP trust elements","checkout speed (express pays)"]

# ------------- Report → insight heuristics (works offline) -------------
SECTION_RX = [
    ("Brand Mentions Overview", r"brand mentions overview[:\-\n]?", re.I),
    ("Customer Sentiment",      r"customer sentiment[:\-\n]?",      re.I),
    ("Engagement Highlights",   r"engagement highlights[:\-\n]?",   re.I),
    ("Streetwear Trends",       r"(streetwear|trend)\s+(themes|trends)[:\-\n]?", re.I),
    ("Competitive Mentions",    r"competitive mentions[:\-\n]?",    re.I),
    ("Opportunities & Risks",   r"opportunities\s*&\s*risks[:\-\n]?", re.I),
    ("Creators",                r"(creators|influencers)[:\-\n]?",  re.I),
    ("Peer Tracker",            r"(peer\s+tracker|scorecard)[:\-\n]?", re.I),
]

def split_sections(text: str) -> Dict[str, str]:
    if not text: return {}
    out: Dict[str, str] = {}
    for title, rx, flags in SECTION_RX:
        m = re.search(rx, text, flags=flags)
        if m:
            start = m.end()
            next_i = len(text)
            for _, rx2, f2 in SECTION_RX:
                if rx2 == rx: continue
                m2 = re.search(rx2, text[start:], flags=f2)
                if m2:
                    next_i = min(next_i, start + m2.start())
            out[title] = text[start:next_i].strip()
    if not out: out["Full Report"] = text.strip()
    return out

def insights_from_sections(brand: Brand, comps: List[Competitor], sections: Dict[str, str]) -> List[Dict[str, Any]]:
    cat = infer_category(brand, comps)
    rows: List[Dict[str, Any]] = []

    if "Brand Mentions Overview" in sections:
        rows.append({"brand": brand.name or "Unknown","competitor":"","signal":"Mentions trend noted","score":60,"note":"section: Brand Mentions Overview"})

    if "Customer Sentiment" in sections:
        tx = sections["Customer Sentiment"].lower()
        score = 70
        if "negative" in tx and "positive" not in tx: score = 40
        elif "positive" in tx and "negative" not in tx: score = 80
        rows.append({"brand": brand.name or "Unknown","competitor":"","signal":"Customer sentiment shift","score":score,"note":"section: Customer Sentiment"})

    if "Engagement Highlights" in sections:
        for h in [ln.strip() for ln in sections["Engagement Highlights"].split("\n") if ln.strip()][:5]:
            rows.append({"brand": brand.name or "Unknown","competitor":"","signal":f"Engagement: {h[:120]}","score":65,"note":"section: Engagement Highlights"})

    if "Competitive Mentions" in sections:
        s = sections["Competitive Mentions"].lower()
        for c in comps[:6]:
            n = (c.name or "").lower()
            if n and n in s:
                rows.append({"brand": brand.name or "Unknown","competitor":c.name,"signal":"Mentioned vs competitor","score":58,"note":"section: Competitive Mentions"})

    if "Opportunities & Risks" in sections:
        for ln in [ln.strip("-• ").strip() for ln in sections["Opportunities & Risks"].split("\n") if ln.strip()][:6]:
            rows.append({"brand": brand.name or "Unknown","competitor":"","signal":ln[:140],"score":70,"note":"section: Opportunities & Risks"})

    # Category-aware scaffolding for differentiation
    for a in audience_archetypes(cat):
        rows.append({"brand": brand.name or "Unknown","competitor":"","signal":f"Audience to activate: {a}","score":55,"note":f"category: {cat}"})
    for cp in creator_playbook(cat):
        rows.append({"brand": brand.name or "Unknown","competitor":"","signal":f"Creator play: {cp['type']} — {cp['activation']}","score":58,"note":f"why: {cp['why']} | {cat}"})
    for f in competitor_focus_points(cat):
        rows.append({"brand": brand.name or "Unknown","competitor":"","signal":f"Competitor focus: {f}","score":57,"note":f"category: {cat}"})

    # Deduplicate
    seen = set(); uniq = []
    for r in rows:
        key = (_slug(r.get("competitor")), _slug(r.get("signal")))
        if key in seen: continue
        seen.add(key); uniq.append(r)
    return uniq

def is_thin(rows: List[Dict[str, Any]]) -> bool:
    if not rows: return True
    return len([r for r in rows if (r.get("signal") or "").strip()]) < THIN_MIN_SIGNALS

def call_openai_structured(brand: Brand, comps: List[Competitor], sections: Dict[str, str]) -> List[Dict[str, Any]]:
    if not OPENAI_API_KEY: return []
    sys_msg = {
        "role":"system",
        "content":(
            "You are a competitive intelligence analyst. Return STRICT JSON only with shape: "
            '{"insights":[{"competitor":"","title":"","score":0,"note":""}]}. '
            "Differentiate by brand category and competitor context. No markdown."
        )
    }
    payload = {"brand": brand.dict(), "competitors": [c.dict() for c in comps], "sections": sections}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"}
    body = {"model": OPENAI_MODEL, "messages":[sys_msg, {"role":"user","content":json.dumps(payload)}], "temperature":0.2}

    with httpx.Client(timeout=OPENAI_TIMEOUT_S) as client:
        r = client.post(OPENAI_CHAT_URL, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

    text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or "{}"
    out: List[Dict[str, Any]] = []
    try:
        parsed = json.loads(text)
        for it in (parsed.get("insights") or []):
            score_val = it.get("score", 0)
            score = int(score_val) if isinstance(score_val, (int,float)) else 0
            out.append({
                "brand": brand.name or "Unknown",
                "competitor": it.get("competitor",""),
                "signal": it.get("title",""),
                "score": score,
                "note": f"source: openai | {it.get('note','')}"
            })
    except Exception:
        pass
    return out

def analyze_core(req: AnalyzeRequest) -> Dict[str, Any]:
    # 1) Build sections from any pasted reports
    joined = "\n\n".join([t for t in req.reports if t and t.strip()])
    sections = split_sections(joined) if joined else {}
    # 2) Heuristic insights from sections
    rows = insights_from_sections(req.brand, req.competitors, sections)
    # 3) Optional OpenAI sharpening
    if "openai" in PROVIDER_ORDER:
        try:
            ai = call_openai_structured(req.brand, req.competitors, sections)
            # merge without dupes
            seen = {(_slug(x.get("competitor")), _slug(x.get("signal"))) for x in rows}
            for r in ai:
                k = (_slug(r.get("competitor")), _slug(r.get("signal")))
                if k not in seen: rows.append(r); seen.add(k)
        except Exception as e:
            print(f"[openai_error] {e}", flush=True)
    # 4) Enrich if thin
    if ENRICH_ON_THIN and is_thin(rows):
        rows += insights_from_sections(req.brand, req.competitors, {})[:6]
    return {
        "ok": True,
        "brand": req.brand.dict(),
        "competitors_count": len(req.competitors),
        "category_inferred": infer_category(req.brand, req.competitors),
        "signals": rows,
        "sections": sections
    }

# ------------- Handlers ---------------------
def _shape_for_ui(result: Dict[str, Any]) -> Dict[str, Any]:
    signals = result.get("signals", [])
    insights = [{
        "competitor": r.get("competitor",""),
        "title": r.get("signal",""),
        "score": r.get("score",0),
        "note": r.get("note",""),
    } for r in signals]
    summary = {
        "brand": result.get("brand",{}).get("name") or "Unknown",
        "competitors_count": result.get("competitors_count",0),
        "category": result.get("category_inferred","unknown"),
        "insight_count": len(insights)
    }
    payload = dict(result)
    payload["insights"] = insights
    payload["summary"]  = summary
    # aliases for older bundles
    payload["results"]  = insights
    payload["data"]     = insights
    payload["items"]    = insights
    return payload

@app.get(f"{API_PREFIX}/health")
def health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": "3.1.0",
        "keys_enabled": bool(APP_API_KEYS),
        "openai_configured": bool(OPENAI_API_KEY),
        "provider_order": PROVIDER_ORDER
    }

@app.get("/api/health")
def health_legacy(): return health()
@app.get("/health")
def health_alias():  return health()

@app.post(f"{API_PREFIX}/intelligence/analyze")
def analyze_prefixed(req: AnalyzeRequest, _=Depends(require_api_key)):
    return _shape_for_ui(analyze_core(req))

@app.post("/intelligence/analyze")
def analyze_alias(req: AnalyzeRequest, _=Depends(require_api_key)):
    return _shape_for_ui(analyze_core(req))

@app.post(f"{API_PREFIX}/intelligence/export")
def export_prefixed(req: AnalyzeRequest, _=Depends(require_api_key)):
    result = analyze_core(req)
    rows = result.get("signals", [])
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["brand","competitor","signal","score","note"])
    w.writeheader()
    for r in rows:
        w.writerow({
            "brand": (req.brand.name or "Unknown"),
            "competitor": r.get("competitor",""),
            "signal": r.get("signal",""),
            "score": r.get("score",""),
            "note": r.get("note",""),
        })
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="signal_scale_export.csv"'}
    )

@app.post("/intelligence/export")
def export_alias(req: AnalyzeRequest, _=Depends(require_api_key)):
    return export_prefixed(req, _)

# ------------- Frontend (serve SPA + assets) -------------
def _find_web_dir() -> str:
    override = os.getenv("WEB_DIR", "").strip()
    if override and os.path.exists(os.path.join(override, "index.html")):
        return override
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "web"),                          # src/api/web
        os.path.join(base, "..", "web"),                    # src/web
        os.path.join(base, "..", "..", "web"),              # repo-root/web
        os.path.join(base, "..", "..", "frontend", "dist"), # repo-root/frontend/dist
        os.path.join(os.getcwd(), "frontend", "dist"),      # CWD/frontend/dist
        os.path.join(os.getcwd(), "web"),
    ]
    for c in map(os.path.abspath, candidates):
        if os.path.exists(os.path.join(c, "index.html")):
            return c
    return os.path.abspath(os.path.join(base, "web"))

WEB_DIR   = _find_web_dir()
INDEX_HTML = os.path.join(WEB_DIR, "index.html")
print(f"[startup] USING WEB_DIR={WEB_DIR} exists={os.path.isdir(WEB_DIR)}", flush=True)
print(f"[startup] INDEX_HTML exists={os.path.exists(INDEX_HTML)}", flush=True)

assets_dir = os.path.join(WEB_DIR, "assets")
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

_DOC_PATHS = {"/openapi.json", "/docs", "/docs/index.html", "/redoc", "/favicon.ico"}

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def root():
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def spa_fallback(full_path: str):
    p = "/" + (full_path or "")
    if p in _DOC_PATHS or p.startswith("/api") or p.startswith("/v1") or p.startswith("/intelligence"):
        # let real handlers handle these
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

@app.get("/debug", response_class=PlainTextResponse)
def debug(_=Depends(require_api_key)):
    demo = analyze_core(AnalyzeRequest(brand=Brand(name="Demo Brand"), competitors=[Competitor(name="Peer A"), Competitor(name="Peer B")]))
    return f"category={demo.get('category_inferred')} insights={len(demo.get('signals',[]))}"
