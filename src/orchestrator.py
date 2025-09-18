# src/orchestrator.py
from __future__ import annotations
import asyncio, time, re
from typing import Any, Dict, List, Optional

from src.collectors.brand_resolver import resolve_brand
from src.collectors.website_collector import collect_site_signals
from src.collectors.ecommerce_collector import collect_ecom_signals
from src.collectors.social_media_collector import collect_social_signals

from src.analyzers.sentiment_analyzer import analyze_sentiment_batch
from src.analyzers.trend_analyzer import extract_trends
from src.analyzers.peer_scorer import score_peer_deltas
from src.analyzers.influence_scorer import rank_influencers

def _nm(x: Any) -> str:
    return (x or "").strip() if isinstance(x, str) else ""

def _parse_name_url(s: str) -> Dict[str, Optional[str]]:
    """Accepts 'adidas, www.adidas.com' or 'adidas | adidas.com' or just 'adidas'."""
    s = (s or "").strip()
    if not s:
        return {"name": None, "url": None}
    # split on comma or pipe
    parts = re.split(r"\s*[|,]\s*", s, maxsplit=1)
    if len(parts) == 1:
        return {"name": parts[0], "url": None}
    return {"name": parts[0], "url": parts[1]}

def _normalize_competitors(raw: List[Dict[str, Any] | str]) -> List[Dict[str, Any]]:
    out = []
    for i, c in enumerate(raw or []):
        if isinstance(c, str):
            parsed = _parse_name_url(c)
            name = _nm(parsed["name"]) or f"Competitor{i+1}"
            url  = _nm(parsed["url"]) or None
        else:
            name = _nm(c.get("name")) or f"Competitor{i+1}"
            url  = _nm(c.get("url")) or None
        out.append({"name": name, "url": url})
    return out

async def _collect_for(entity_name: str, entity_url: Optional[str]) -> Dict[str, Any]:
    site = await collect_site_signals(entity_url)
    ecom = await collect_ecom_signals(entity_url)
    social = await collect_social_signals(entity_name, window_days=7)
    return {"site": site, "ecom": ecom, "social": social}

async def run_analysis(
    brand: Dict[str, Any],
    competitors: List[Dict[str, Any] | str],
    window_days: int = 7,
    mode: str = "all",
) -> Dict[str, Any]:
    t0 = time.perf_counter()

    # 1) Normalize inputs
    b_name = _nm(brand.get("name")) or _nm(brand.get("url")) or "Brand"
    b_url  = _nm(brand.get("url")) or None
    comps  = _normalize_competitors(competitors)

    # 2) Resolve brand + competitors (official domain + category/summary)
    brand_resolved = await resolve_brand(b_name, hint_url=b_url)
    b_domain = brand_resolved.get("official_domain") or b_url
    b_category = brand_resolved.get("category") or "apparel"

    comp_resolved = await asyncio.gather(*[
        resolve_brand(c["name"], hint_url=c["url"]) for c in comps
    ])
    comp_domains = [
        (c["name"], r.get("official_domain") or c["url"], r) for c, r in zip(comps, comp_resolved)
    ]

    # 3) Collect signals concurrently for *each* entity against its own domain
    brand_bundle, *comp_bundles = await asyncio.gather(
        _collect_for(b_name, b_domain),
        *[_collect_for(name, url) for (name, url, _r) in comp_domains],
    )

    # 4) Sentiment (short-circuit on empty)
    brand_texts = [p["text"] for p in brand_bundle["social"].get("posts", []) if p.get("text")]
    comp_texts  = [p["text"] for b in comp_bundles for p in b["social"].get("posts", []) if p.get("text")]

    brand_sent  = await analyze_sentiment_batch(brand_texts)
    comp_sent   = await analyze_sentiment_batch(comp_texts)

    # 5) Trends
    brand_trends = extract_trends(brand_bundle["social"].get("posts", []))
    market_trends = extract_trends([p for b in comp_bundles for p in b["social"].get("posts", [])])

    # 6) Peer deltas with category weight
    peer = score_peer_deltas(
        brand={"name": b_name, "site": brand_bundle["site"], "ecom": brand_bundle["ecom"]},
        competitors=[{"name": name, "site": bun["site"], "ecom": bun["ecom"]}
                     for (name, _url, _r), bun in zip(comp_domains, comp_bundles)],
        category=b_category
    )

    # 7) Influencers / creators to watch
    infl = rank_influencers(brand_bundle["social"], [b["social"] for b in comp_bundles])

    # 8) Assemble response
    signals = peer["signals"] + infl["signals"]
    summary = {
        "brand": b_name,
        "competitors": [name for (name, _url, _r) in comp_domains],
        "window_days": window_days,
        "category": b_category,
        "resolved_domain": b_domain,
        "resolver_confidence": brand_resolved.get("confidence"),
        "timing_ms": int((time.perf_counter() - t0) * 1000),
        "counts": {
            "brand_posts": len(brand_bundle["social"].get("posts", [])),
            "comp_posts": sum(len(b["social"].get("posts", [])) for b in comp_bundles),
        },
        "notes": {
            "brand_resolved_from": brand_resolved.get("source"),
            "comp_domains": [{ "name": name, "domain": url, "conf": r.get("confidence") } for (name, url, r) in comp_domains]
        }
    }

    report = {
        "strengths": peer.get("strengths", [])[:5],
        "gaps": peer.get("gaps", [])[:5],
        "priorities": peer.get("priorities", [])[:5],
        "brand_trends": brand_trends[:10],
        "market_trends": market_trends[:10],
        "sentiment": {
            "brand": brand_sent,
            "competitors": comp_sent,
        },
        "brand_profile": {
            "summary": brand_resolved.get("summary"),
            "category": b_category,
            "domain": b_domain,
            "confidence": brand_resolved.get("confidence"),
        }
    }

    return {
        "ok": True,
        "summary": summary,
        "signals": signals,
        "report": report,
        "evidence": {
            "brand": brand_bundle,
            "competitors": [
                {"name": name, "bundle": bun, "resolved": r}
                for (name, _url, r), bun in zip(comp_domains, comp_bundles)
            ],
        },
    }
