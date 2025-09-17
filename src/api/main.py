# main.py — Signal & Scale API (v3.0, no-Manus mode with report ingest)
# Dependencies:
#   fastapi, uvicorn[standard], httpx, pydantic, python-multipart, pypdf, python-docx (optional)
# Add to requirements.txt:
# fastapi==0.115.0
# uvicorn[standard]==0.30.6
# httpx==0.27.2
# pydantic==2.8.2
# python-multipart==0.0.9
# pypdf==5.0.1
# python-docx==1.1.2

import os, io, csv, json, re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, Request, Header, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# -------------------- App --------------------
API_PREFIX = os.getenv("API_PREFIX", "/api").rstrip("/")  # default '/api'
app = FastAPI(title="Signal & Scale", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    resp = await call_next(request)
    print(f"{request.method} {request.url.path} -> {resp.status_code}", flush=True)
    return resp

# -------------------- Auth (customer app keys) --------------------
def _load_keys(env_name: str) -> List[str]:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return []
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
    # NEW: direct report input
    reports: List[str] = Field(default_factory=list)       # pasted text blobs
    report_urls: List[str] = Field(default_factory=list)   # (future) remote fetch, not used now
    class Config: extra = "ignore"

# Better 422 visibility
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.json()
    except Exception:
        body = "<non-JSON or unreadable>"
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body_received": body})

# -------------------- Provider config --------------------
PROVIDER_ORDER = [p.strip().lower() for p in os.getenv("PROVIDER_ORDER", "openai").split(",") if p.strip()]

# OpenAI (primary for this build)
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_CHAT_URL  = os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions").strip()
OPENAI_TIMEOUT_S = float(os.getenv("OPENAI_TIMEOUT_S", "60"))

# Thin-result enrichment
ENRICH_ON_THIN   = os.getenv("ENRICH_ON_THIN", "true").lower() == "true"
THIN_MIN_SIGNALS = int(os.getenv("THIN_MIN_SIGNALS", "2"))

# -------------------- Category heuristics --------------------
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

# -------------------- Report Extraction (files or text) --------------------
def extract_text_from_upload(content: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join([p.extract_text() or "" for p in reader.pages])
        except Exception as e:
            return f"[pdf_read_error:{e}]"
    if name.endswith(".docx"):
        try:
            import docx
            d = docx.Document(io.BytesIO(content))
            return "\n".join([p.text for p in d.paragraphs])
        except Exception as e:
            return f"[docx_read_error:{e}]"
    if name.endswith(".csv"):
        try:
            text = content.decode("utf-8", errors="ignore")
            return text
        except Exception as e:
            return f"[csv_decode_error:{e}]"
    # default to text
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return ""

SECTION_HINTS = [
    ("Brand Mentions Overview", r"brand mentions overview[:\-\n]?", 1.0),
    ("Customer Sentiment", r"customer sentiment[:\-\n]?", 1.0),
    ("Engagement Highlights", r"engagement highlights[:\-\n]?", 1.0),
    ("Streetwear Trends", r"(streetwear|trend)\s+(themes|trends)[:\-\n]?", 0.8),
    ("Competitive Mentions", r"competitive mentions[:\-\n]?", 0.9),
    ("Opportunities & Risks", r"opportunities\s*&\s*risks[:\-\n]?", 1.0),
    ("Creators", r"(creators|influencers)[:\-\n]?", 0.8),
    ("Peer Tracker", r"(peer\s+tracker|scorecard)[:\-\n]?", 0.8),
]

def crude_sections(text: str) -> Dict[str, str]:
    """Split the pasted report into rough sections based on headings."""
    out: Dict[str, str] = {}
    norm = text or ""
    for title, rx, _w in SECTION_HINTS:
        m = re.search(rx, norm, flags=re.I)
        if m:
            start = m.end()
            # find next heading or end
            next_idx = len(norm)
            for _, rx2, _w2 in SECTION_HINTS:
                if rx2 == rx: continue
                m2 = re.search(rx2, norm[m.end():], flags=re.I)
                if m2:
                    next_idx = min(next_idx, m.end() + m2.start())
            out[title] = norm[start:next_idx].strip()
    if not out:
        out["Full Report"] = norm.strip()
    return out

def insights_from_sections(brand: Brand, comps: List[Competitor], sections: Dict[str, str]) -> List[Dict[str, Any]]:
    """Turn extracted sections into structured, renderable rows."""
    cat = infer_category(brand, comps)
    rows: List[Dict[str, Any]] = []

    # Heuristic pulls
    if "Brand Mentions Overview" in sections:
        rows.append({"brand": brand.name or "Unknown", "competitor":"", "signal":"Mentions trend noted (see overview)", "score":60, "note":"source: report | section: Brand Mentions Overview"})

    if "Customer Sentiment" in sections:
        tx = sections["Customer Sentiment"].lower()
        score = 70
        if "negative" in tx and "positive" not in tx: score = 40
        elif "positive" in tx and "negative" not in tx: score = 80
        rows.append({"brand": brand.name or "Unknown", "competitor":"", "signal":"Customer sentiment shift detected", "score":score, "note":"source: report | section: Customer Sentiment"})

    if "Engagement Highlights" in sections:
        highlights = sections["Engagement Highlights"].split("\n")
        for h in highlights[:5]:
            h = h.strip()
            if len(h) > 6:
                rows.append({"brand": brand.name or "Unknown", "competitor":"", "signal":f"Engagement: {h[:120]}", "score":65, "note":"source: report | section: Engagement Highlights"})

    if "Competitive Mentions" in sections:
        for c in comps[:6]:
            n = (c.name or "").lower()
            if n and n in sections["Competitive Mentions"].lower():
                rows.append({"brand": brand.name or "Unknown", "competitor":c.name, "signal":"Brand is mentioned vs this competitor", "score":58, "note":"source: report | section: Competitive Mentions"})

    if "Opportunities & Risks" in sections:
        lines = [ln.strip("-• ").strip() for ln in sections["Opportunities & Risks"].split("\n") if ln.strip()]
        for ln in lines[:6]:
            rows.append({"brand": brand.name or "Unknown", "competitor":"", "signal":ln[:140], "score":70, "note":"source: report | section: Opportunities & Risks"})

    # Category-aware creator & focus scaffolding
    for a in audience_archetypes(cat):
        rows.append({"brand": brand.name or "Unknown", "competitor":"", "signal": f"Audience to activate: {a}", "score":55, "note": f"category: {cat} | source: strategy"})
    for cp in creator_playbook(cat):
        rows.append({"brand": brand.name or "Unknown", "competitor":"", "signal": f"Creator play: {cp['type']} — {cp['activation']}", "score":58, "note": f"why: {cp['why']} | category: {cat} | source: strategy"})
    for f in competitor_focus_points(cat):
        rows.append({"brand": brand.name or "Unknown", "competitor":"", "signal": f"Competitor focus: {f}", "score":57, "note": f"category: {cat} | source: strategy"})

    # Dedupe by (competitor, signal)
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for r in rows:
        key = (_slug(r.get("competitor")), _slug(r.get("signal")))
        if key in seen: continue
        seen.add(key)
        uniq.append(r)
    return uniq

# -------------------- OpenAI synthesis (optional but recommended) --------------------
def call_openai_structured(brand: Brand, comps: List[Competitor], sections: Dict[str, str]) -> List[Dict[str, Any]]:
    if not OPENAI_API_KEY:
        return []
    sys_msg = {
        "role":"system",
        "content":(
            "You are a competitive intelligence analyst. Return STRICT JSON only with shape: "
            '{"insights":[{"competitor":"","title":"","score":0,"note":""}]}. '
            "Differentiate by brand category and competitor context. No markdown or prose."
        )
    }
    payload = {
        "brand": brand.dict(),
        "competitors": [c.dict() for c in comps],
        "sections": sections
    }
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
            score = int(score_val) if isinstance(score_val, (int, float)) else 0
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

# -------------------- Core --------------------
def analyze_core(req: AnalyzeRequest) -> Dict[str, Any]:
    # 1) Gather text: pasted reports (and, if you add, uploaded files)
    joined = "\n\n".join([t for t in req.reports if t and t.strip()])
    sections = crude_sections(joined) if joined else {}

    # 2) Heuristic insights from sections (works even without OpenAI)
    rows = insights_from_sections(req.brand, req.competitors, sections)

    # 3) OpenAI synthesis (if available) to sharpen and brand-differentiate further
    if "openai" in PROVIDER_ORDER:
        try:
            ai_rows = call_openai_structured(req.brand, req.competitors, sections)
            rows = _merge_rows(rows, ai_rows)
        except Exception as e:
            print(f"[openai_error] {type(e).__name__}: {e}", flush=True)

    # 4) Enrich if thin
    if ENRICH_ON_THIN and is_thin(rows):
        # Add a few category scaffolds again (guarantee something shows)
        rows = _merge_rows(rows, insights_from_sections(req.brand, req.competitors, sections)[:8])

    # 5) Final payload
    return {
        "ok": True,
        "brand": req.brand.dict(),
        "competitors_count": len(req.competitors),
        "category_inferred": infer_category(req.brand, req.competitors),
        "signals": rows,
        "sections": sections
    }

def _merge_rows(a: List[Dict[str, Any]], b: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = {(_slug(x.get("competitor")), _slug(x.get("signal"))) for x in a}
    out = list(a)
    for r in b:
        key = (_slug(r.get("competitor")), _slug(r.get("signal")))
        if key not in seen:
            out.append(r); seen.add(key)
    return out

def is_thin(rows: List[Dict[str, Any]]) -> bool:
    if not rows: return True
    meaningful = [r for r in rows if (r.get("signal") or "").strip()]
    return len(meaningful) < THIN_MIN_SIGNALS

# -------------------- API --------------------
@app.get(f"{API_PREFIX}/health")
def health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": "3.0.0",
        "keys_enabled": bool(APP_API_KEYS),
        "openai_configured": bool(OPENAI_API_KEY),
        "provider_order": PROVIDER_ORDER
    }

@app.get("/api/health")
def health_legacy(): return health()
@app.get("/health")
def health_alias():  return health()

# Ingest: upload files (PDF/DOCX/TXT/CSV). Returns extracted text chunks for you to feed into analyze.
@app.post(f"{API_PREFIX}/intelligence/ingest")
async def ingest_files(files: List[UploadFile] = File(...), _=Depends(require_api_key)):
    blobs: List[str] = []
    for f in files:
        data = await f.read()
        text = extract_text_from_upload(data, f.filename)
        if text and text.strip():
            blobs.append(text[:200000])  # guard huge files
    # Return uniformly so the frontend can stuff this into AnalyzeRequest.reports
    return {"ok": True, "reports": blobs, "count": len(blobs)}

# Analyze (prefixed)
@app.post(f"{API_PREFIX}/intelligence/analyze")
def analyze_prefixed(req: AnalyzeRequest, _=Depends(require_api_key)):
    return _analyze_response(req)

# Analyze (alias without prefix)
@app.post("/intelligence/analyze")
def analyze_alias(req: AnalyzeRequest, _=Depends(require_api_key)):
    return _analyze_response(req)

def _analyze_response(req: AnalyzeRequest) -> Dict[str, Any]:
    result = analyze_core(req)
    signals = result.get("signals", [])
    insights = [{"competitor": r.get("competitor",""), "title": r.get("signal",""), "score": r.get("score",0), "note": r.get("note","")} for r in signals]
    summary = {
        "brand": result.get("brand", {}).get("name") or "Unknown",
        "competitors_count": result.get("competitors_count", 0),
        "category": result.get("category_inferred", "unknown"),
        "insight_count": len(insights)
    }
    payload = dict(result)
    payload["insights"] = insights
    payload["summary"]  = summary
    # aliases for any legacy UI bundle keys
    payload["results"]  = insights
    payload["data"]     = insights
    payload["items"]    = insights
    return payload

# CSV export (uses analyze_core internally)
@app.post(f"{API_PREFIX}/intelligence/export")
def export_prefixed(req: AnalyzeRequest, _=Depends(require_api_key)):
    return _export_csv(req)
@app.post("/intelligence/export")
def export_alias(req: AnalyzeRequest, _=Depends(require_api_key)):
    return _export_csv(req)

def _export_csv(req: AnalyzeRequest):
    result = analyze_core(req)
    rows = result.get("signals", [])
    buf = io.StringIO()
    fieldnames = ["brand","competitor","signal","score","note"]
    w = csv.DictWriter(buf, fieldnames=fieldnames); w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k,"") for k in fieldnames})
    return StreamingResponse(io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="signal_scale_export.csv"'}
    )

# -------------------- Frontend (serve / + assets) --------------------
def find_web_dir() -> str:
    override = os.getenv("WEB_DIR", "").strip()
    if override and os.path.exists(os.path.join(override, "index.html")):
        return override
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "web"),
        os.path.join(base_dir, "..", "web"),
        os.path.join(base_dir, "..", "..", "web"),
        os.path.join(base_dir, "..", "..", "frontend", "dist"),
        os.path.join(os.getcwd(), "frontend", "dist"),
        os.path.join(os.getcwd(), "web"),
    ]
    for c in map(os.path.abspath, candidates):
        if os.path.exists(os.path.join(c, "index.html")):
            return c
    return os.path.abspath(os.path.join(base_dir, "web"))

WEB_DIR = find_web_dir()
INDEX_HTML = os.path.join(WEB_DIR, "index.html")
print(f"[startup] USING WEB_DIR={WEB_DIR} exists={os.path.isdir(WEB_DIR)}", flush=True)
print(f"[startup] INDEX_HTML exists={os.path.exists(INDEX_HTML)}", flush=True)

assets_dir = os.path.join(WEB_DIR, "assets")
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

DOC_PATHS = {"/openapi.json", "/docs", "/docs/index.html", "/redoc", "/favicon.ico"}

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def root():
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def spa_fallback(full_path: str):
    p = "/" + (full_path or "")
    if p in DOC_PATHS or p.startswith("/api") or p.startswith("/v1") or p.startswith("/intelligence"):
        raise HTTPException(status_code=404, detail="Not found")
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

@app.api_route("/favicon.ico", methods=["GET", "HEAD"])
def favicon():
    ico_path = os.path.join(WEB_DIR, "favicon.ico")
    if os.path.exists(ico_path): return FileResponse(ico_path)
    return HTMLResponse("", status_code=204)
