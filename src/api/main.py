# src/api/main.py — Signal & Scale v4.0.1 (clean)
import os, io, csv, json, re, time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

API_PREFIX = os.getenv("API_PREFIX", "/api").rstrip("/")
app = FastAPI(title="Signal & Scale", version="4.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

def _log(s: str): print(s, flush=True)

@app.middleware("http")
async def _log_req(req, call_next):
    resp = await call_next(req)
    _log(f"{req.method} {req.url.path} -> {resp.status_code}")
    return resp

def _load_keys(env_name: str) -> List[str]:
    raw = os.getenv(env_name, "").strip()
    return [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()] if raw else []

APP_API_KEYS = _load_keys("API_KEYS")

def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if APP_API_KEYS and (x_api_key not in APP_API_KEYS):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key

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
    reports: List[str] = Field(default_factory=list)  # optional pasted text
    class Config: extra = "ignore"

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    body = "<unreadable>"
    try:
        body = (await request.body()).decode("utf-8", errors="ignore")
    except Exception:
        pass
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body_received": body})

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
    return ["lifestyle shoppers","UGC reviewers","deal hunters","campus creators"]

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

ENABLE_PROBES = os.getenv("ENABLE_PROBES", "true").lower() != "false"
PSI_API_KEY   = os.getenv("PSI_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

def probe_site(url: str, timeout=10.0) -> Dict[str, Any]:
    if not url: return {"ok": False, "reason":"no_url"}
    u = url if url.startswith("http") else f"https://{url}"
    headers = {"User-Agent":"SignalScale/1.0"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(u)
            ttfb = r.elapsed.total_seconds()
            html = r.text[:200_000]
            size_kb = len(r.content) / 1024.0
    except Exception as e:
        return {"ok": False, "url": u, "reason": f"{type(e).__name__}: {e}"}

    def has(patterns: List[str]) -> bool:
        hay = html.lower()
        return any(p.lower() in hay for p in patterns)

    return {
        "ok": True,
        "url": u,
        "status": r.status_code,
        "ttfb_ms": int(ttfb*1000),
        "bytes_kb": round(size_kb, 1),
        "has_shop_pay": has(["Shop Pay","shop-pay-button","shopPay"]),
        "has_apple_pay": has(["Apple Pay","apple-pay"]),
        "has_klarna": has(["Klarna"]),
        "has_afterpay": has(["Afterpay","After Pay"]),
        "has_reviews": has(["reviews","yotpo","okendo","judge.me","loox"]),
        "has_size_chart": has(["size chart","size guide"]),
        "has_video": has(["<video","youtube.com","vimeo.com"]),
        "has_collab_story": has(["collab","collaboration","capsule","collection story"]),
        "has_blog_editorial": has(["blog","editorial","journal","stories"]),
        "mobile_meta": has(['name="viewport"','content="width=device-width']),
    }

def fetch_pagespeed(url: str) -> Dict[str, Any]:
    if not PSI_API_KEY or not url: return {}
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "key": PSI_API_KEY, "strategy": "mobile"}
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(endpoint, params=params)
            if r.status_code != 200: return {}
            data = r.json()
            lhr = (data.get("lighthouseResult") or {})
            cat = (lhr.get("categories") or {}).get("performance") or {}
            audits = (lhr.get("audits") or {})
            return {
                "psi_perf_score": round((cat.get("score") or 0)*100),
                "psi_cls": (audits.get("cumulative-layout-shift") or {}).get("numericValue"),
                "psi_lcp": (audits.get("largest-contentful-paint") or {}).get("numericValue"),
                "psi_tti": (audits.get("interactive") or {}).get("numericValue"),
            }
    except Exception:
        return {}

def youtube_mentions(brand: str, max_items=5) -> List[Dict[str, Any]]:
    if not YOUTUBE_API_KEY or not brand: return []
    q = f"{brand} streetwear"
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {"part":"snippet", "q": q, "type":"video", "maxResults": max_items, "key": YOUTUBE_API_KEY}
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url, params=params)
            if r.status_code != 200: return []
            items = r.json().get("items", [])
            out = []
            for it in items:
                sn = it.get("snippet", {})
                out.append({
                    "title": sn.get("title"),
                    "channel": sn.get("channelTitle"),
                    "published": sn.get("publishedAt"),
                    "videoId": (it.get("id") or {}).get("videoId"),
                })
            return out
    except Exception:
        return []

PROVIDER_ORDER = [p.strip().lower() for p in os.getenv("PROVIDER_ORDER", "openai").split(",") if p.strip()]
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_CHAT_URL  = os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions").strip()
OPENAI_TIMEOUT_S = float(os.getenv("OPENAI_TIMEOUT_S", "45"))
ENRICH_ON_THIN   = os.getenv("ENRICH_ON_THIN", "true").lower() == "true"
THIN_MIN_SIGNALS = int(os.getenv("THIN_MIN_SIGNALS", "3"))

def synthesize_with_openai(brand: Brand, comps: List[Competitor], facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "openai" not in PROVIDER_ORDER or not OPENAI_API_KEY: return []
    sys = {
        "role":"system",
        "content":(
            "You are a decisive competitive intelligence operator. "
            "Given JSON facts about a brand, its competitors, and site probes, "
            "return STRICT JSON: {\"insights\":[{\"competitor\":\"\",\"title\":\"\",\"score\":0,\"note\":\"\"}]} "
            "— 6-12 items, no markdown."
        )
    }
    user = {"role":"user","content":json.dumps({
        "brand": brand.dict(),
        "competitors":[c.dict() for c in comps],
        "facts": facts
    }, ensure_ascii=False)}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"}
    body = {"model": OPENAI_MODEL, "messages":[sys, user], "temperature":0.2}

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

def heuristic_insights(req: AnalyzeRequest, facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cat = facts.get("category","unknown")
    probes = facts.get("probes", {})

    b = probes.get("brand") or {}
    if b.get("ok"):
        if not b.get("mobile_meta"): rows.append({"brand": req.brand.name, "competitor":"", "signal":"Missing/weak mobile meta viewport", "score":45, "note":"UX/Mobile"})
        if not b.get("has_reviews"): rows.append({"brand": req.brand.name, "competitor":"", "signal":"Add reviews widget to PDPs", "score":62, "note":"Trust/Conversion"})
        if b.get("ttfb_ms", 800) > 1200: rows.append({"brand": req.brand.name, "competitor":"", "signal":f"Slow TTFB ~{b['ttfb_ms']}ms — cache/CDN tune", "score":58, "note":"Speed"})

    for c in req.competitors:
        key = c.name or ""
        p = probes.get(key) or {}
        if not p: continue
        if p.get("has_video"): rows.append({"brand": req.brand.name, "competitor": c.name, "signal":"Competitor uses rich PDP video", "score":60, "note":"Raise PDP media richness"})
        if p.get("has_collab_story"): rows.append({"brand": req.brand.name, "competitor": c.name, "signal":"Competitor leans on collaboration storytelling", "score":57, "note":"Editorial/Collab hub"})
        if p.get("has_apple_pay") and not b.get("has_apple_pay"): rows.append({"brand": req.brand.name, "competitor": c.name, "signal":"Competitor offers Apple Pay; parity recommended", "score":63, "note":"Checkout friction"})

    for a in audience_archetypes(cat):
        rows.append({"brand": req.brand.name, "competitor":"", "signal": f"Audience to activate: {a}", "score":55, "note": f"category: {cat}"})
    for cp in creator_playbook(cat):
        rows.append({"brand": req.brand.name, "competitor":"", "signal": f"Creator play: {cp['type']} — {cp['activation']}", "score":58, "note": f"why: {cp['why']} | {cat}"})
    for f in competitor_focus_points(cat):
        rows.append({"brand": req.brand.name, "competitor":"", "signal": f"Competitor focus: {f}", "score":57, "note": f"category: {cat}"})

    if facts.get("youtube", {}).get(req.brand.name or "brand"):
        rows.append({"brand": req.brand.name, "competitor":"", "signal":"YouTube chatter detected — mine creators for collab fits", "score":59, "note":"social"})

    seen, uniq = set(), []
    for r in rows:
        k = (_slug(r.get("competitor")), _slug(r.get("signal")))
        if k not in seen:
            uniq.append(r); seen.add(k)
    return uniq

def build_facts(req: AnalyzeRequest) -> Dict[str, Any]:
    cat = infer_category(req.brand, req.competitors)
    facts: Dict[str, Any] = {"category": cat, "probes": {}, "pagespeed": {}, "youtube": {}}

    if ENABLE_PROBES:
        probes: Dict[str, Any] = {}
        for idx, item in enumerate([req.brand] + req.competitors):
            key = "brand" if idx == 0 else (item.name or f"competitor_{idx}")
            probes[key] = probe_site(item.url or item.name or "")
            if PSI_API_KEY and (item.url or ""):
                facts["pagespeed"][key] = fetch_pagespeed(item.url)
        facts["probes"] = probes

    yts = youtube_mentions(req.brand.name or "")
    if yts: facts["youtube"][req.brand.name or "brand"] = yts

    if req.reports:
        joined = "\n\n".join([t for t in req.reports if t.strip()])
        facts["report_text"] = joined[:200000]

    return facts

def analyze_core(req: AnalyzeRequest) -> Dict[str, Any]:
    facts = build_facts(req)
    rows = heuristic_insights(req, facts)
    try:
        rows_ai = synthesize_with_openai(req.brand, req.competitors, facts)
        seen = {(_slug(x.get("competitor")), _slug(x.get("signal"))) for x in rows}
        for r in rows_ai:
            k = (_slug(r.get("competitor")), _slug(r.get("signal")))
            if k not in seen: rows.append(r); seen.add(k)
    except Exception as e:
        _log(f"[openai_error] {e}")

    if ENRICH_ON_THIN and (len([r for r in rows if (r.get("signal") or '').strip()]) < THIN_MIN_SIGNALS):
        rows += heuristic_insights(req, {"category": infer_category(req.brand, req.competitors), "probes": {}})[:6]

    return {
        "ok": True,
        "brand": req.brand.dict(),
        "competitors_count": len(req.competitors),
        "category_inferred": infer_category(req.brand, req.competitors),
        "facts": {"pagespeed_used": bool(PSI_API_KEY), "youtube_used": bool(YOUTUBE_API_KEY), "probes_enabled": ENABLE_PROBES},
        "signals": rows
    }

def _shape_for_ui(result: Dict[str, Any]) -> Dict[str, Any]:
    signals = result.get("signals", [])
    insights = [{
        "competitor": r.get("competitor",""),
        "title": r.get("signal",""),
        "score": r.get("score",0),
        "note": r.get("note",""),
    } for r in signals]
    payload = dict(result)
    payload["insights"] = insights
    payload["summary"]  = {
        "brand": result.get("brand",{}).get("name") or "Unknown",
        "competitors_count": result.get("competitors_count",0),
        "category": result.get("category_inferred","unknown"),
        "insight_count": len(insights)
    }
    payload["results"] = payload["data"] = payload["items"] = insights
    return payload

@app.get(f"{API_PREFIX}/health")
def health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": "4.0.1",
        "keys_enabled": bool(APP_API_KEYS),
        "openai_configured": bool(OPENAI_API_KEY),
        "provider_order": PROVIDER_ORDER,
        "pagespeed": bool(PSI_API_KEY),
        "youtube": bool(YOUTUBE_API_KEY),
        "probes": ENABLE_PROBES
    }

@app.get("/api/health")
def health_legacy(): return health()
@app.get("/health")
def health_alias():  return health()

@app.post(f"{API_PREFIX}/intelligence/analyze")
def analyze_pref(req: AnalyzeRequest, _=Depends(require_api_key)):
    return _shape_for_ui(analyze_core(req))

@app.post("/intelligence/analyze")
def analyze_alias(req: AnalyzeRequest, _=Depends(require_api_key)):
    return _shape_for_ui(analyze_core(req))

@app.post(f"{API_PREFIX}/intelligence/export")
def export_pref(req: AnalyzeRequest, _=Depends(require_api_key)):
    result = analyze_core(req)
    rows = result.get("signals", [])
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["brand","competitor","signal","score","note"])
    w.writeheader()
    brand_name = (req.brand.name or "Unknown")
    for r in rows:
        w.writerow({
            "brand": brand_name,
            "competitor": r.get("competitor",""),
            "signal": r.get("signal",""),
            "score": r.get("score",""),
            "note": r.get("note",""),
        })
    # ✅ FIX: header quotes were broken before
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="signal_scale_export.csv"'}
    )

@app.post("/intelligence/export")
def export_alias(req: AnalyzeRequest, _=Depends(require_api_key)):
    return export_pref(req, _)

def _find_web_dir() -> str:
    override = os.getenv("WEB_DIR", "").strip()
    if override and os.path.exists(os.path.join(override, "index.html")): return override
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "web"),
        os.path.join(base, "..", "web"),
        os.path.join(base, "..", "..", "web"),
        os.path.join(base, "..", "..", "frontend", "dist"),
        os.path.join(os.getcwd(), "frontend", "dist"),
        os.path.join(os.getcwd(), "web"),
    ]
    for c in map(os.path.abspath, candidates):
        if os.path.exists(os.path.join(c, "index.html")): return c
    return os.path.abspath(os.path.join(base, "web"))

WEB_DIR = _find_web_dir()
INDEX_HTML = os.path.join(WEB_DIR, "index.html")
_log(f"[startup] USING WEB_DIR={WEB_DIR} exists={os.path.isdir(WEB_DIR)}")
_log(f"[startup] INDEX_HTML exists={os.path.exists(INDEX_HTML)}")

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

from fastapi import HTTPException
@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def spa_fallback(full_path: str):
    p = "/" + (full_path or "")
    if p in _DOC_PATHS or p.startswith("/api") or p.startswith("/v1") or p.startswith("/intelligence"):
        raise HTTPException(status_code=404, detail="Not found")
    if not os.path.exists(INDEX_HTML):
        return HTMLResponse(f"<h1>Frontend not found</h1><p>Expected: <code>{INDEX_HTML}</code></p>", status_code=500)
    return FileResponse(INDEX_HTML)

@app.get("/debug", response_class=PlainTextResponse)
def debug(_=Depends(require_api_key)):
    demo = analyze_core(AnalyzeRequest(
        brand=Brand(name="Demo Brand", url="example.com"),
        competitors=[Competitor(name="Peer A", url="https://stussy.com"), Competitor(name="Peer B", url="https://hufworldwide.com")]
    ))
    return f"category={demo.get('category_inferred')} insights={len(demo.get('signals',[]))}"
