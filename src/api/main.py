# src/api/main.py
from __future__ import annotations

import csv
import io
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
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

APP_VERSION = "3.0.0"

# --------- Paths (serve frontend from frontend/dist) ---------
HERE = os.path.dirname(os.path.abspath(__file__))
# ../../frontend/dist relative to this file
FRONTEND_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "frontend", "dist"))
# Allow override from env if you want
FRONTEND_DIR = os.environ.get("WEB_DIR", FRONTEND_DIR)

# --------- FastAPI init ---------
app = FastAPI(
    title="Signal & Scale",
    version=APP_VERSION,
    docs_url="/openapi.json",  # keep openapi JSON at /openapi.json
    redoc_url=None,
    swagger_ui_oauth2_redirect_url=None,
)

# Basic CORS (relaxed — tighten for production domains if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # set to your domain(s) in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Static serving (no-cache for css/js to avoid stale UI) ---------
class NoCacheStatic(StaticFiles):
    async def get_response(self, path: str, scope):
        resp = await super().get_response(path, scope)
        # CSS/JS/json/map shouldn't be cached while you're iterating
        if any(path.endswith(ext) for ext in (".css", ".js", ".json", ".map")):
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
        return resp

if os.path.isdir(FRONTEND_DIR):
    app.mount("/web", NoCacheStatic(directory=FRONTEND_DIR, html=True), name="web")

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

# --------- Utilities ---------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

def _normalize_name(url_or_name: Optional[str]) -> str:
    if not url_or_name:
        return ""
    s = url_or_name.strip()
    if s.startswith("http"):
        try:
            host = re.sub(r"^https?://", "", s)
            host = host.split("/")[0]
            host = host.replace("www.", "")
            host = host.split(":")[0]
            return host
        except Exception:
            return s
    return s

async def quick_site_probe(url: Optional[str]) -> Dict[str, Any]:
    """Very fast HEAD/GET probe to detect basic shop/checkout signals."""
    if not url:
        return {"reachable": False, "shop_pay": False, "apple_pay": False, "klarna": False, "checkout_steps": None}

    if not url.startswith("http"):
        url = "https://" + url

    res_info: Dict[str, Any] = {
        "reachable": False,
        "status": None,
        "server": None,
        "shop_pay": False,
        "apple_pay": False,
        "klarna": False,
        "checkout_steps": None,
    }
    t0 = time.perf_counter()
    timeout = httpx.Timeout(6.0, connect=3.0)
    headers = {"User-Agent": "SignalScale/1.0 (+https://signal-scale.app)"}

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = await client.get(url)
            res_info["status"] = r.status_code
            res_info["server"] = r.headers.get("server")
            res_info["reachable"] = (200 <= r.status_code < 400)
            text = (r.text or "")[:100_000].lower()
            res_info["shop_pay"] = ("shop pay" in text) or ("shop.app/pay" in text)
            res_info["apple_pay"] = ("apple pay" in text) or ("apple-pay" in text)
            res_info["klarna"] = "klarna" in text
            # naive checkout step heuristic
            hints = sum(1 for kw in ("/cart", "/checkout", "checkout") if kw in text)
            res_info["checkout_steps"] = min(3, max(1, hints)) if hints else None
    except Exception:
        pass
    finally:
        res_info["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return res_info

def synthesize_insights(brand: Brand, comps: List[Competitor], probes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """LLM-assisted if OPENAI is present; otherwise heuristic insights."""
    # Aggregate probe facts
    def badge(site: Dict[str, Any]) -> List[str]:
        b = []
        if site.get("shop_pay"): b.append("Shop Pay")
        if site.get("apple_pay"): b.append("Apple Pay")
        if site.get("klarna"): b.append("Klarna")
        if site.get("checkout_steps"): b.append(f"{site['checkout_steps']}-step checkout")
        return b

    summary: Dict[str, Any] = {
        "brand": brand.name or _normalize_name(brand.url) or "Brand",
        "competitors": [c.name or _normalize_name(c.url) for c in comps],
        "window_days": None,
    }

    signals: List[Dict[str, Any]] = []
    b_site = probes.get("brand") or {}
    for c in comps:
        c_key = (c.name or _normalize_name(c.url) or "competitor").lower()
        c_site = probes.get(c_key) or {}
        # Simple scoring heuristic
        b_pay = int(b_site.get("shop_pay") or b_site.get("apple_pay") or b_site.get("klarna") or 0)
        c_pay = int(c_site.get("shop_pay") or c_site.get("apple_pay") or c_site.get("klarna") or 0)
        b_latency = b_site.get("latency_ms") or 9999
        c_latency = c_site.get("latency_ms") or 9999

        comp_name = c.name or _normalize_name(c.url) or "Competitor"
        # Gap or strength based on payments and latency
        if c_pay and not b_pay:
            signals.append({
                "brand": summary["brand"],
                "competitor": comp_name,
                "signal": "Checkout trust gap",
                "note": f"{comp_name} shows pay options ({', '.join(badge(c_site))}); add accelerated pay on PDP/checkout.",
                "score": 82,
                "source": {"brand_site": brand.url, "competitor_site": c.url, "probe": "payments"},
            })
        if c_latency + 200 < b_latency:
            signals.append({
                "brand": summary["brand"],
                "competitor": comp_name,
                "signal": "Site performance gap",
                "note": f"{comp_name} home loads faster (~{c_latency}ms vs {b_latency}ms). Audit hero weight, defer non-critical JS.",
                "score": 74,
                "source": {"brand_site": brand.url, "competitor_site": c.url, "probe": "latency"},
            })
        if b_pay and not c_pay:
            signals.append({
                "brand": summary["brand"],
                "competitor": comp_name,
                "signal": "Trust advantage",
                "note": f"You surface accelerated pay ({', '.join(badge(b_site))}); emphasize above the fold on PDP.",
                "score": 68,
                "source": {"brand_site": brand.url, "competitor_site": c.url, "probe": "payments"},
            })

    # If no signals yet, add a baseline
    if not signals:
        signals.append({
            "brand": summary["brand"],
            "competitor": None,
            "signal": "Baseline",
            "note": "No clear checkout/speed deltas detected. Add competitor PDP audits to uncover content gaps (video, size chart, UGC).",
            "score": 50,
            "source": {"probe": "baseline"},
        })

    result = {"ok": True, "summary": summary, "signals": signals, "probes": probes}

    # Optional: LLM enrichment (kept minimal; no background calls if no key)
    if OPENAI_API_KEY and len(signals) > 0:
        try:
            import asyncio
            from httpx import Timeout
            # Use OpenAI Responses API via HTTP (keeps deps minimal)
            system = (
                "You are a retail brand intelligence strategist. "
                "Given site probes and gaps, return 3 prioritized, high-impact moves "
                "for the next 30 days. Be specific, measurable, and channel-aware."
            )
            user = json.dumps({"brand": brand.model_dump(), "competitors": [c.model_dump() for c in comps], "probes": probes, "signals": signals})
            payload = {
                "model": "gpt-4o-mini",
                "input": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_output_tokens": 600,
            }
            async def call_openai():
                async with httpx.AsyncClient(timeout=Timeout(20.0)) as client:
                    r = await client.post(
                        "https://api.openai.com/v1/responses",
                        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    r.raise_for_status()
                    data = r.json()
                    # The Responses API returns output in 'output_text' (convenience) when present
                    text = data.get("output_text") or json.dumps(data, indent=2)
                    return text
            text = asyncio.get_event_loop().run_until_complete(call_openai())
            result["recommendations"] = text
        except Exception as e:
            result["llm_error"] = str(e)

    return result

# --------- Routes ---------
@app.get("/api/health")
async def api_health():
    return {
        "ok": True,
        "service": "signal-scale",
        "version": APP_VERSION,
        "frontend_dir_exists": os.path.isdir(FRONTEND_DIR),
        "frontend_dir": FRONTEND_DIR,
        "openai_configured": bool(OPENAI_API_KEY),
    }

@app.post("/api/intelligence/analyze")
async def analyze(req: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None, convert_underscores=False)):
    # Optional header-based simple auth:
    required_keys = (os.environ.get("API_KEYS") or "").split(",") if os.environ.get("API_KEYS") else []
    if required_keys:
        token = (x_api_key or "").strip()
        if token not in [k.strip() for k in required_keys if k.strip()]:
            raise HTTPException(status_code=401, detail="Invalid API key")

    # Run quick probes for brand + competitors
    probes: Dict[str, Dict[str, Any]] = {}
    key_brand = (req.brand.name or _normalize_name(req.brand.url) or "brand").lower()
    probes["brand"] = await quick_site_probe(req.brand.url)
    for c in req.competitors:
        key = (c.name or _normalize_name(c.url) or "competitor").lower()
        probes[key] = await quick_site_probe(c.url)

    result = synthesize_insights(req.brand, req.competitors, probes)
    return JSONResponse(result)

@app.post("/api/intelligence/export")
async def export_csv(req: AnalyzeRequest):
    # Reuse analyze logic for now
    probes: Dict[str, Dict[str, Any]] = {}
    probes["brand"] = await quick_site_probe(req.brand.url)
    for c in req.competitors:
        key = (c.name or _normalize_name(c.url) or "competitor").lower()
        probes[key] = await quick_site_probe(c.url)
    data = synthesize_insights(req.brand, req.competitors, probes)

    # Build CSV
    output = io.StringIO()
    w = csv.writer(output)
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
    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    headers = {"Content-Disposition": 'attachment; filename="signal_scale_export.csv"'}
    return StreamingResponse(csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)

# --------- Root + SPA fallback ---------
def _index_path() -> str:
    return os.path.join(FRONTEND_DIR, "index.html")

@app.get("/", response_class=HTMLResponse)
async def root():
    if not os.path.isfile(_index_path()):
        return HTMLResponse(
            f"<h1>Frontend not found</h1><p>Expected: { _index_path() }</p>",
            status_code=404,
        )
    return FileResponse(_index_path())

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    # Serve SPA index.html for any non-API path
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    if not os.path.isfile(_index_path()):
        return HTMLResponse(
            f"<h1>Frontend not found</h1><p>Expected: { _index_path() }</p>",
            status_code=404,
        )
    return FileResponse(_index_path())

# --------- Debug (optional) ---------
@app.get("/debug", response_class=PlainTextResponse)
async def debug():
    lines = [
        f"version: {APP_VERSION}",
        f"FRONTEND_DIR: {FRONTEND_DIR}",
        f"exists: {os.path.isdir(FRONTEND_DIR)}",
        f"OPENAI configured: {bool(OPENAI_API_KEY)}",
    ]
    try:
        if os.path.isdir(FRONTEND_DIR):
            files = sorted(os.listdir(FRONTEND_DIR))
            lines.append("files: " + ", ".join(files[:30]))
    except Exception as e:
        lines.append(f"ls error: {e}")
    return PlainTextResponse("\n".join(lines))
