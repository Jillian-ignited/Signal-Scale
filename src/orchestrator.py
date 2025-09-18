# src/orchestrator.py
from __future__ import annotations
import asyncio, time
from typing import Any, Dict, List

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

async def run_analysis(
    brand: Dict[str, Any],
    competitors: List[Dict[str, Any]],
    window_days: int = 7,
    mode: str = "all",
) -> Dict[str, Any]:
    t0 = time.perf_counter()

    # 0) Resolve brand canonical info (official site + category) for confidence
    b_name = _nm(brand.get("name")) or _nm(brand.get("url")) or "Brand"
    b_url  = _nm(brand.get("url"))
    resolved = await resolve_brand(b_name, hint_url=b_url)
    official_domain = resolved.get("official_domain")
    category = resolved.get("category") or "apparel"
    b_url_final = b_url or (official_domain if official_domain else None)

    comps = [{"name": _nm(c.get("name")) or _nm(c.get("url")) or f"Competitor{i+1}",
              "url": _nm(c.get("url"))}
             for i,c in enumerate(competitors or [])]

    async def collect_for(entity_name: str, entity_url: str | None):
        site = await collect_site_signals(entity_url or official_domain)
        ecom = await collect_ecom_signals(entity_url or official_domain)
        social = await collect_social_signals(entity_name, window_days=window_days)
        return {"site": site, "ecom": ecom, "social": social}

    # 1) Collect concurrently
    brand_bundle, *comp_bundles = await asyncio.gather(
        collect_for(b_name, b_url_final),
        *[collect_for(c["name"], c["url"]) for c in comps]
    )

    # 2) Sentiment
    brand_texts = [p["text"] for p in brand_bundle["social"].get("posts", []) if p.get("text")]
    comp_texts = [p["text"] for b in comp_bundles for p in b["social"].get("posts", []) if p.get("text")]
    brand_sent = await analyze_sentiment_batch(brand_texts)
    comp_sent  = await analyze_sentiment_batch(comp_texts)

    # 3) Trends
    brand_trends = extract_trends(brand_bundle["social"].get("posts", []))
    comp_trends  = extract_trends([p for b in comp_bundles for p in b["social"].get("posts", [])])

    # 4) Peer deltas with category weight
    peer = score_peer_deltas(
        brand={"name": b_name, "site": brand_bundle["site"], "ecom": brand_bundle["ecom"]},
        competitors=[{"name": c["name"], "site": b["site"], "ecom": b["ecom"]} for c,b in zip(comps, comp_bundles)],
        category=category
    )

    # 5) Influencers
    infl = rank_influencers(brand_bundle["social"], [b["social"] for b in comp_bundles])

    # 6) Assemble
    signals = peer["signals"] + infl["signals"]
    summary = {
        "brand": b_name,
        "competitors": [c["name"] for c in comps],
        "window_days": window_days,
        "category": category,
        "resolved_domain": official_domain,
        "resolver_confidence": resolved.get("confidence"),
        "timing_ms": int((time.perf_counter() - t0) * 1000),
        "counts": {
            "brand_posts": len(brand_bundle["social"].get("posts", [])),
            "comp_posts": sum(len(b["social"].get("posts", [])) for b in comp_bundles),
        },
    }

    report = {
        "strengths": peer.get("strengths", [])[:5],
        "gaps": peer.get("gaps", [])[:5],
        "priorities": peer.get("priorities", [])[:5],
        "brand_trends": brand_trends[:10],
        "market_trends": comp_trends[:10],
        "sentiment": {
            "brand": brand_sent,
            "competitors": comp_sent,
        },
        "brand_profile": {
            "summary": resolved.get("summary"),
            "category": category,
            "domain": official_domain,
            "confidence": resolved.get("confidence"),
        }
    }

    return {
        "ok": True,
        "summary": summary,
        "signals": signals,
        "report": report,
        "evidence": {
            "brand": brand_bundle,
            "competitors": [{**c, "bundle": b} for c,b in zip(comps, comp_bundles)],
        },
    }
