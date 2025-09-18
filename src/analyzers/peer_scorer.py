# src/analyzers/peer_scorer.py
from __future__ import annotations
from typing import Dict, Any, List

def score_peer_deltas(brand: Dict[str, Any], competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
    bsite = brand.get("site", {})
    becom = brand.get("ecom", {})
    signals: List[Dict[str, Any]] = []
    strengths, gaps, priorities = [], [], []

    b_lat = bsite.get("latency_ms")
    b_pay = brand_has_accelerated_pay(bsite)

    for c in competitors:
        cname = c.get("name") or "Competitor"
        csite = c.get("site", {})
        c_lat = csite.get("latency_ms")
        c_pay = brand_has_accelerated_pay(csite)

        # Performance gap
        if isinstance(b_lat, int) and isinstance(c_lat, int) and c_lat + 200 < b_lat:
            note = f"{cname} faster (~{c_lat}ms vs {b_lat}ms). Compress hero, defer non-critical JS."
            signals.append(sig(brand["name"], cname, "Performance gap", note, 74, {"type": "latency"}))
            gaps.append("Improve homepage speed: image compression, lazy-loading, JS splitting.")
            priorities.append("Speed audit + Lighthouse fixes (High)")

        # Trust/payments
        if c_pay and not b_pay:
            note = f"{cname} surfaces accelerated pay (Shop Pay / Apple Pay / Klarna)."
            signals.append(sig(brand["name"], cname, "Checkout trust gap", note, 82, {"type": "payments"}))
            gaps.append("Expose accelerated pay above-the-fold on PDP and mini-cart.")
            priorities.append("Add Shop Pay / Apple Pay / Klarna (High)")
        if b_pay and not c_pay:
            signals.append(sig(brand["name"], cname, "Trust advantage", "Maintain accelerated pay prominence.", 68, {"type": "payments"}))
            strengths.append("Accelerated pay supported—keep badges visible near ATC.")

        # Shopify samples
        c_shop_cnt = (c.get("ecom", {}).get("platform_data") or {}).get("shopify_products_count")
        b_shop_cnt = (becom.get("platform_data") or {}).get("shopify_products_count")
        if c_shop_cnt and not b_shop_cnt:
            signals.append(sig(brand["name"], cname, "Catalog transparency gap", "Competitor exposes product JSON; consider public catalog endpoints.", 55, {"type": "catalog"}))

    # Deduplicate / trim
    strengths = list(dict.fromkeys(strengths))[:5]
    gaps = list(dict.fromkeys(gaps))[:5]
    priorities = _unique_priorities(priorities)

    return {"signals": signals, "strengths": strengths, "gaps": gaps, "priorities": priorities}

def brand_has_accelerated_pay(site: Dict[str, Any]) -> bool:
    p = (site.get("payments") or {})
    return bool(p.get("shop_pay") or p.get("apple_pay") or p.get("klarna"))

def sig(brand: str, comp: str | None, label: str, note: str, score: int, source: Dict[str, Any]) -> Dict[str, Any]:
    return {"brand": brand, "competitor": comp, "signal": label, "note": note, "score": score, "source": source}

def _unique_priorities(items: List[str]) -> List[str]:
    out = []
    seen = set()
    for it in items:
        if it not in seen:
            out.append(it); seen.add(it)
    return out[:5]
