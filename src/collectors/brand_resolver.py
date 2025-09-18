# src/collectors/brand_resolver.py
from __future__ import annotations
import httpx, re, unicodedata
from typing import Dict, Any, Optional

UA = {"User-Agent": "SignalScaleBot/1.0"}
WIKI_SEARCH = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json&srlimit=1"
WIKI_PAGE = "https://en.wikipedia.org/w/api.php?action=query&prop=extracts|info|extlinks|categories&inprop=url&explaintext=1&format=json&pageids={pid}&ellimit=500&cllimit=500"

SKIP_DOMAINS = re.compile(
    r"(web\.archive\.org|facebook\.com|instagram\.com|x\.com|twitter\.com|tiktok\.com|youtube\.com|linkedin\.com|pinterest\.com)",
    re.I,
)

def _strip_accents(s: str) -> str:
    # “Stüssy” -> “Stussy”
    nfkd = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def _tokenize(name: str) -> str:
    base = _strip_accents(name).lower()
    return re.sub(r"[^a-z0-9]+", "", base)

def _clean_host(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    u = u.strip()
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    u = u.split("/")[0].lower()
    return u or None

def _pick_official(extlinks, brand_token: str) -> Optional[str]:
    if not isinstance(extlinks, list):
        return None
    brand_token = (brand_token or "").lower()
    best = None
    for e in extlinks:
        url = e.get("*") if isinstance(e, dict) else None
        if not url:
            continue
        host = _clean_host(url)
        if not host or SKIP_DOMAINS.search(host):
            continue
        # prefer domain that contains token (e.g., stussy.com)
        if brand_token and brand_token in host:
            return host
        if best is None:
            best = host
    return best

def _category_from_categories(cats) -> str:
    if not isinstance(cats, list):
        return "unknown"
    labels = " ".join([c.get("title", "") for c in cats]).lower()
    if "streetwear" in labels:
        return "streetwear"
    if "athletic" in labels or "sportswear" in labels:
        return "athletic"
    if "luxury" in labels:
        return "luxury"
    if "skate" in labels:
        return "skate"
    return "apparel"

async def resolve_brand(brand_name: str, hint_url: Optional[str] = None) -> Dict[str, Any]:
    brand_name = (brand_name or "").strip()
    token = _tokenize(brand_name)[:24]
    out = {
        "resolved_name": brand_name,
        "official_domain": _clean_host(hint_url) if hint_url else None,
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
            hits = (sr.json().get("query", {}) or {}).get("search", []) or []
            if not hits:
                return out
            pid = hits[0].get("pageid")
            if not pid:
                return out

            pr = await client.get(WIKI_PAGE.format(pid=pid))
            if pr.status_code != 200:
                return out
            page = (pr.json().get("query", {}) or {}).get("pages", {}).get(str(pid), {}) or {}

            extract = page.get("extract")
            extlinks = page.get("extlinks") or []
            cats = page.get("categories") or []

            official = _pick_official(extlinks, token)
            if official:
                out["official_domain"] = official

            out["summary"] = (extract or "")[:1200] if extract else None
            out["category"] = _category_from_categories(cats)
            out["confidence"] = 0.9 if out["official_domain"] and out["summary"] else 0.7
            return out
    except Exception:
        return out
