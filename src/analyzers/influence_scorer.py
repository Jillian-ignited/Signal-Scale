# src/analyzers/influence_scorer.py
from __future__ import annotations
from typing import Dict, Any, List

def rank_influencers(brand_social: Dict[str, Any], comps_social: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Very lightweight: treat high-score reddit posts / unique YT titles as 'influencers'.
    This is a placeholder until you wire Manus or full creator APIs.
    """
    signals: List[Dict[str, Any]] = []
    posts = (brand_social or {}).get("posts", []) + [p for s in (comps_social or []) for p in s.get("posts", [])]
    posts = posts[:50]

    # crude signal: posts with score/comments → surface as "creators to watch"
    ranked = sorted(posts, key=lambda p: (p.get("score") or 0, p.get("comments") or 0), reverse=True)[:5]
    for p in ranked:
        title = (p.get("title") or "")[:120]
        url = p.get("url")
        signals.append({
            "brand": None,
            "competitor": None,
            "signal": "Creator to watch",
            "note": f"{title} — {url}",
            "score": 60,
            "source": {"type": p.get("platform") or "social"}
        })
    return {"signals": signals}
