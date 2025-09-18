# src/analyzers/peer_scorer.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple

def brand_has_accelerated_pay(site: Dict[str, Any]) -> bool:
    p = (site.get("payments") or {})
    return bool(p.get("shop_pay") or p.get("apple_pay") or p.get("klarna"))

def _conf(v) -> float:
    return 1.0 if v else 0.4

def _cat_weight(cat: str, label: str) -> float:
    """
    Category-aware emphasis. Example: in athletic, speed and size-guides matter more;
    in streetwear, UGC/editorial and drops cadence matter (once we collect them).
    For now, bias a few signals.
    """
    cat = (cat or "apparel").lower()
    if "athletic" in cat and "Performance" in label: return 1.2
    if "street" in cat and "Trust" in label: return 1.1
    return 1.0

def sig(brand: str, comp: str | None, label: str, note: str, score: int, source: Dict[str, Any], w: float = 1.0, conf: float = 0.9) -> Dict[str, Any]:
    s = max(1, min(100, int(round(score * w))))
    return {"brand": brand, "competitor": comp, "signal": label, "note": note, "score": s, "confidence": round(conf,2), "source": source}

def score_peer_deltas(brand: Dict[str, Any], competitors: List[Dict[str, Any]], category: str | None = None) -> Dict[str, Any]:
    bsite = brand.get("site", {})
    becom = brand.get("ecom", {})
    bname = brand.get("name") or "Brand"

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
            base = 74
            w = _cat_weight(category, "Performance gap")
            note = f"{cname} homepage loads faster (~{c_lat}ms vs {b_lat}ms). Compress hero, lazy-load images, split JS."
            signals.append(sig(bname, cname, "Performance gap", note, base, {"type": "latency"}, w=w, conf=_conf(True)))
            gaps.append("Improve homepage speed (LCP <2.5s).")
            priorities.append("Speed audit + image/JS optimizations (High)")

        # Trust/payments
        if c_pay and not b_pay:
            base = 82
            w = _cat_weight(category, "Checkout trust gap")
            note = f"{cname} surfaces accelerated pay (Shop Pay / Apple Pay / Klarna). Add badges near ATC & mini-cart."
            signals.append(sig(bname, cname, "Checkout trust gap", note, base, {"type": "payments"}, w=w, conf=_conf(True)))
            gaps.append("Expose accelerated pay above-the-fold on PDP.")
            priorities.append("Add Shop Pay / Apple Pay / Klarna (High)")

        if b_pay and not c_pay:
            base = 68
            w = _cat_weight(category, "Trust advantage")
            signals.append(sig(bname, cname, "Trust advantage", "Maintain accelerated pay prominence.", base, {"type": "payments"}, w=w, conf=_conf(True)))
            strengths.append("Accelerated pay supported—keep badges visible.")

        # Shopify product samples visibility
        c_shop_cnt = (c.get("ecom", {}).get("platform_data") or {}).get("shopify_products_count")
        b_shop_cnt = (becom.get("platform_data") or {}).get("shopify_products_count")
        if c_shop_cnt and not b_shop_cnt:
            signals.append(sig(bname, cname, "Catalog transparency gap", "Competitor exposes product JSON; consider public catalog endpoints.", 55, {"type": "catalog"}, w=_cat_weight(category, "Catalog transparency")))
            gaps.append("Enable lightweight public catalog endpoint for discovery tools.")
            priorities.append("Expose products.json subset (Medium)")

    # dedupe/trim
    strengths = list(dict.fromkeys(strengths))[:5]
    gaps = list(dict.fromkeys(gaps))[:5]
    priorities = _unique(priorities)[:5]

    return {"signals": signals, "strengths": strengths, "gaps": gaps, "priorities": priorities}

def _unique(items: List[str]) -> List[str]:
    out = []; seen = set()
    for it in items:
        if it not in seen:
            out.append(it); seen.add(it)
    return out
