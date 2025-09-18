# src/collectors/website_collector.py
from __future__ import annotations
import re, httpx, asyncio
from typing import Dict, Any, List, Optional

UA = {"User-Agent": "SignalScaleBot/1.0 (+https://signal-scale.app)"}

def _title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

def _og_site(html: str) -> str:
    m = re.search(r'<meta\s+property=["\']og:site_name["\']\s+content=["\']([^"\']+)["\']', html or "", re.I)
    return (m.group(1) or "").strip() if m else ""

def _has_payment_clues(html: str) -> Dict[str, bool]:
    h = (html or "").lower()
    return {
        "shop_pay": "shop pay" in h or "shopify-payment-button" in h,
        "apple_pay": "apple pay" in h or "apple-pay" in h,
        "klarna": "klarna" in h or "x.klarnacdn" in h,
    }

def _platform_clues(html: str, headers: httpx.Headers) -> Dict[str, bool]:
    h = (html or "").lower()
    server = " ".join(headers.get_list("server")).lower()
    return {
        "shopify": ("cdn.shopify.com" in h) or ("shopify" in server),
        "bigcommerce": "bigcommerce" in h or "bigcommerce" in server,
        "commerce": "commercejs" in h or "commerce.js" in h,
    }

async def _get(url: str) -> httpx.Response | None:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(7.0, connect=3.0), headers=UA, follow_redirects=True) as c:
            return await c.get(url)
    except Exception:
        return None

async def collect_site_signals(url: Optional[str]) -> Dict[str, Any]:
    if not url:
        return {"url": None, "reachable": False, "status": None, "latency_ms": None,
                "title": None, "og_site": None,
                "payments": {"shop_pay": False, "apple_pay": False, "klarna": False},
                "platform": {"shopify": False, "bigcommerce": False, "commerce": False},
                "pdp_cues": {"size_chart": False, "reviews": False, "video": False}
                }

    main = await _get(url if url.startswith("http") else f"https://{url}")
    if not (main and main.status_code < 400):
        return {"url": url, "reachable": False, "status": main.status_code if main else None, "latency_ms": None,
                "title": None, "og_site": None,
                "payments": {"shop_pay": False, "apple_pay": False, "klarna": False},
                "platform": {"shopify": False, "bigcommerce": False, "commerce": False},
                "pdp_cues": {"size_chart": False, "reviews": False, "video": False}
                }

    html = main.text or ""
    pay = _has_payment_clues(html)
    plat = _platform_clues(html, main.headers)

    # quick PDP probe: look for product links pattern
    pdp_links = []
    for m in re.finditer(r'href=["\'](/products/[^"\']+)["\']', html, re.I):
        pdp_links.append(m.group(1))
        if len(pdp_links) >= 3: break

    async def _pdp_probe(path: str) -> Dict[str, bool]:
        r = await _get(f"https://{main.request.url.host}{path}")
        if not (r and r.status_code < 400): return {"size_chart": False, "reviews": False, "video": False}
        h = r.text.lower()
        return {
            "size_chart": "size chart" in h or "size-guide" in h or "size_guide" in h,
            "reviews": "review" in h or "rating" in h or 'itemprop="reviewRating"' in h,
            "video": "<video" in h or "youtube.com/embed" in h or "vimeo.com" in h,
        }

    pdp_signals = {"size_chart": False, "reviews": False, "video": False}
    if pdp_links:
        probes = await asyncio.gather(*[_pdp_probe(p) for p in pdp_links], return_exceptions=True)
        for p in probes:
            if isinstance(p, dict):
                for k in pdp_signals:
                    pdp_signals[k] = pdp_signals[k] or p.get(k, False)

    return {
        "url": str(main.request.url).split("?")[0],
        "reachable": True,
        "status": main.status_code,
        "latency_ms": int(main.elapsed.total_seconds() * 1000) if main.elapsed else None,
        "title": _title(html),
        "og_site": _og_site(html),
        "payments": pay,
        "platform": plat,
        "pdp_cues": pdp_signals,
    }
