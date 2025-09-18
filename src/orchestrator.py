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

def _split_name_url(s: str) -> (Optional[str], Optional[str]):
    s = (s or "").strip()
    if not s: return None, None
    parts = re.split(r"\s*[|,]\s*", s, maxsplit=1)
    if len(parts) == 1: return parts[0], None
    return parts[0], parts[1]

def _normalize_competitors(raw: List[Dict[str, Any] | str]) -> List[Dict[str, Any]]:
    out = []
    for i, c in enumerate(raw or []):
        name, url = None, None
        if isinstance(c, str):
            name, url = _split_name_url(c)
        else:
            name = _nm(c.get("name"))
            url  = _nm(c.get("url")) or None
            # if name holds "adidas, www.adidas.com" and url is empty → split
            if (not url) and name and ("," in name or "|" in name):
                n2, u2 = _split_name_url(name)
                if n2: name = n2
                if u2: url  = u2
        out.append({"name": name or f"Competitor{i+1}", "url": url})
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

    # Normalize inputs
    b_name = _nm(brand.get("name")) or _nm(brand.get("url")) or "Brand"
    b_url  = _nm(brand.get("url")) or None
    comps  = _normalize_competitors(competitors)

    # Resolve entities
    brand_resolved = await resolve_brand(b_name, hint_url=b_url)
    b_domain = brand_resolved.get("official_domain") or b_url
    b_category = brand_resolved.get("category") or "apparel"
    b_clean_name = brand_resolved.get("resolved_name") or b_name

    comp_resolved = await asyncio.gather(*[
        resolve_brand(c["name"], hint_url=c["url"]) for c in comps
    ])
    comp_info = [
        {
            "input_name": c["name"],
            "resolved_name": r.get("resolved_name") or c["name"],
            "domain": r.get("official_domain") or c["url"],
            "confidence": r.get("confidence"),
            "resolver": r,
        }
        for c, r in zip(comps, comp_resolved)
    ]

    # Collect
    brand_bundle, *comp_bundles = await asyncio.gather(
        _collect_for(b_clean_name, b_domain),
        *[_collect_for(ci["resolved_name"], ci["domain"]) for ci in comp_info],
    )

    # Sentiment
    brand_texts = [p["text"] for p in brand_bundle["social"].get("posts", []) if p.get("text")]
    comp_texts  = [p["text"] for b in comp_bundles for p in b["social"].get("posts", []) if p.get("text")]

    brand_sent  = await analyze_sentiment_batch(brand_texts)
    comp_sent   = await analyze_sentiment_batch(comp_texts)

    # Trends
    brand_trends  = extract_trends(brand_bundle["social"].get("posts", []))
    market_trends = extract_trends([p for b in comp_bundles for p in b["social"].get("posts", [])])

    # Peer deltas
    peer = score_peer_deltas(
        brand={"name": b_clean_name, "site": brand_bundle["site"], "ecom": brand_bundle["ecom"]},
        competitors=[{"name": ci["resolved_name"], "site": bun["site"], "ecom": bun["ecom"]}
                     for ci, bun in zip(comp_info, comp_bundles)],
        category=b_category
    )

    infl = rank_influencers(brand_bundle["social"], [b["social"] for b in comp_bundles])

    signals = peer["signals"] + infl["signals"]
    summary = {
        "brand": b_clean_name,
        "competitors": [ci["resolved_name"] for ci in comp_info],
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
            "comp_domains": [{"name": ci["resolved_name"], "domain": ci["domain"], "conf": ci["confidence"]} for ci in comp_info]
        }
    }

    report = {
        "strengths": peer.get("strengths", [])[:5],
        "gaps":      peer.get("gaps", [])[:5],
        "priorities":peer.get("priorities", [])[:5],
        "brand_trends":  brand_trends[:10],
        "market_trends": market_trends[:10],
        "sentiment": {"brand": brand_sent, "competitors": comp_sent},
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
                {"name": ci["resolved_name"], "bundle": bun, "resolved": ci["resolver"]}
                for ci, bun in zip(comp_info, comp_bundles)
            ],
        },
    }
