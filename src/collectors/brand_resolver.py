# src/collectors/brand_resolver.py
from __future__ import annotations
import httpx, re, unicodedata
from typing import Dict, Any, Optional, List

UA = {"User-Agent": "SignalScaleBot/1.0 (+https://signal-scale.app)"}

SOCIAL_HOSTS = re.compile(
    r"(facebook\.com|instagram\.com|x\.com|twitter\.com|tiktok\.com|youtube\.com|linkedin\.com|pinterest\.com|web\.archive\.org)",
    re.I,
)

def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def _token(name: str) -> str:
    base = _strip_accents(name).lower()
    return re.sub(r"[^a-z0-9]+", "", base)

def _clean_host(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    u = u.strip()
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    return u.split("/")[0].lower() if u else None

async def _fetch(url: str, *, timeout: float = 6.0, headers: dict | None = None) -> httpx.Response | None:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=3.0), headers=headers or UA, follow_redirects=True) as c:
            r = await c.get(url)
            return r
    except Exception:
        return None

def _looks_like_official(host: str, brand_token: str) -> bool:
    if SOCIAL_HOSTS.search(host or ""):
        return False
    return brand_token in (host or "")

def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

def _extract_og_site(html: str) -> str:
    m = re.search(r'<meta\s+property=["\']og:site_name["\']\s+content=["\']([^"\']+)["\']', html or "", re.I)
    return (m.group(1) or "").strip() if m else ""

async def _verify_brand_on_home(host: str, brand_token: str) -> float:
    """Return confidence 0..1 based on homepage signals."""
    if not host:
        return 0.0
    r = await _fetch(f"https://{host}/")
    if not (r and r.status_code < 400):
        r = await _fetch(f"http://{host}/")
    if not (r and r.status_code < 400):
        return 0.0
    html = r.text or ""
    title = _extract_title(html).lower()
    ogs   = _extract_og_site(html).lower()
    score = 0.0
    if brand_token and (brand_token in title or brand_token in ogs):
        score += 0.6
    # bonus if not a marketplace/platform
    if not re.search(r"(shopify\.com|bigcommerce\.com|amazon\.com|ebay\.com|farfetch\.com|ssense\.com)", host):
        score += 0.2
    # bonus if https and 200ish
    if str(r.status_code).startswith("2"):
        score += 0.2
    return min(1.0, score)

async def _heuristic_domains(brand_token: str) -> List[str]:
    # Try common TLDs first
    base = [f"{brand_token}.com", f"{brand_token}.co", f"{brand_token}.net"]
    # Also handle “and/&” brands like “crooksandcastles”
    base2 = []
    if "and" not in brand_token and "&" in brand_token:
        bt2 = brand_token.replace("&", "and")
        base2 = [f"{bt2}.com", f"{bt2}.co", f"{bt2}.net"]
    return list(dict.fromkeys(base + base2))  # dedupe, keep order

async def _ddg_pick(brand_name: str, brand_token: str) -> Optional[str]:
    # DuckDuckGo HTML search – parse first non-social result
    q = brand_name.replace(" ", "+")
    url = f"https://duckduckgo.com/html/?q={q}+official+site"
    r = await _fetch(url)
    if not (r and r.status_code == 200):
        return None
    html = r.text or ""
    # Very light HTML parsing for result URLs
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', html):
        link = m.group(1)
        host = _clean_host(link)
        if not host or SOCIAL_HOSTS.search(host):
            continue
        out.append(host)
    # Pick first that contains the brand token if any; else first result
    for h in out:
        if _looks_like_official(h, brand_token):
            return h
    return out[0] if out else None

async def resolve_brand(brand_name: str, hint_url: Optional[str] = None) -> Dict[str, Any]:
    brand_name = (brand_name or "").strip()
    brand_token = _token(brand_name)[:30]
    out = {
        "resolved_name": brand_name,
        "official_domain": _clean_host(hint_url) if hint_url else None,
        "summary": None,            # not using Wikipedia
        "category": "apparel",      # leave generic unless your pipeline classifies
        "confidence": 0.2,
        "source": "resolver",
    }
    # 1) If you provided a URL, verify it
    if out["official_domain"]:
        conf = await _verify_brand_on_home(out["official_domain"], brand_token)
        out["confidence"] = max(out["confidence"], conf)
        return out

    # 2) Try exact-domain heuristics
    for host in await _heuristic_domains(brand_token):
        conf = await _verify_brand_on_home(host, brand_token)
        if conf >= 0.7:
            out["official_domain"] = host
            out["confidence"] = conf
            return out
        if conf >= 0.4 and not out["official_domain"]:
            out["official_domain"] = host
            out["confidence"] = conf

    # 3) Fall back to a search pick (no API key)
    host = await _ddg_pick(brand_name, brand_token)
    if host:
        conf = await _verify_brand_on_home(host, brand_token)
        out["official_domain"] = host
        out["confidence"] = max(out["confidence"], conf if conf > 0 else 0.5)

    return out
