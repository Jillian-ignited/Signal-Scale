# src/collectors/brand_resolver.py
from __future__ import annotations
import httpx, re
from typing import Dict, Any, Optional

UA = {"User-Agent": "SignalScaleBot/1.0"}
WIKI_SEARCH = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json&srlimit=1"
WIKI_PAGE = "https://en.wikipedia.org/w/api.php?action=query&prop=extracts|info|extlinks|categories&inprop=url&explaintext=1&format=json&pageids={pid}&ellimit=500&cllimit=500"

def _clean_url(u: Optional[str]) -> Optional[str]:
    if not u: return None
    u = u.strip()
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    u = u.split("/")[0]
    return u.lower() if u else None

def _pick_official(extlinks) -> Optional[str]:
    if not isinstance(extlinks, list): return None
    # Heuristic: prefer brand top-level domain
    best = None
    for e in extlinks:
        url = e.get("*") if isinstance(e, dict) else None
        if not url: continue
        # ignore social domains
        if re.search(r"(facebook|instagram|twitter|x\.com|tiktok|youtube|linkedin|pinterest)", url, re.I):
            continue
        best = url
        # strong hint
        if re.search(r"\.com/?$", url): 
            return best
    return best

def _category_from_categories(cats) -> str:
    if not isinstance(cats, list): return "unknown"
    labels = " ".join([c.get("title","") for c in cats]).lower()
    if "streetwear" in labels: return "streetwear"
    if "athletic" in labels or "sportswear" in labels: return "athletic"
    if "luxury" in labels or "high fashion" in labels: return "luxury"
    if "denim" in labels: return "denim"
    if "skateboarding" in labels: return "skate"
    return "apparel"

async def resolve_brand(brand_name: str, hint_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Uses Wikipedia to reliably resolve:
      - official website
      - plain-text summary
      - category guess
    Works well for Nike, Stüssy, etc. Private/obscure brands fall back to hint_url.
    """
    brand_name = (brand_name or "").strip()
    out = {
        "resolved_name": brand_name,
        "official_domain": _clean_url(hint_url) if hint_url else None,
        "summary": None,
        "category": "unknown",
        "confidence": 0.4 if hint_url else 0.2,
        "source": "wikipedia",
    }
    if not brand_name:
        return out

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), headers=UA) as client:
            sr = await client.get(WIKI_SEARCH.format(q=brand_name.replace(" ", "+")))
            if sr.status_code != 200:
                return out
            sdata = sr.json()
            hits = (sdata.get("query", {}) or {}).get("search", []) or []
            if not hits:
                return out
            pid = hits[0].get("pageid")
            if not pid:
                return out

            pr = await client.get(WIKI_PAGE.format(pid=pid))
            if pr.status_code != 200:
                return out
            pdata = pr.json()
            page = (pdata.get("query", {}) or {}).get("pages", {}).get(str(pid), {}) or {}

            extract = page.get("extract")
            extlinks = page.get("extlinks") or []
            cats = page.get("categories") or []
            official = _pick_official(extlinks)
            if official:
                out["official_domain"] = _clean_url(official)

            out["summary"] = (extract or "")[:1200] if extract else None
            out["category"] = _category_from_categories(cats)
            # raise confidence if we found official site + summary
            conf = 0.7
            if out["official_domain"] and out["summary"]:
                conf = 0.9
            out["confidence"] = conf
            return out
    except Exception:
        return out
