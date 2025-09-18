# src/collectors/website_collector.py
from __future__ import annotations
import time, httpx, re
from typing import Dict, Any
from .base_collector import normalize_url

UA = {"User-Agent": "SignalScale/1.0 (+https://signal-scale.app)"}

async def collect_site_signals(url: str | None) -> Dict[str, Any]:
    url = normalize_url(url)
    out: Dict[str, Any] = {
        "url": url, "reachable": False, "status": None, "latency_ms": None,
        "payments": {"shop_pay": False, "apple_pay": False, "klarna": False},
        "platform": {"shopify": False, "bigcommerce": False, "commerce": False},
        "pdp_cues": {"size_chart": False, "reviews": False, "video": False}
    }
    if not url:
        return out

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), follow_redirects=True, headers=UA) as client:
            r = await client.get(url)
            out["status"] = r.status_code
            out["reachable"] = 200 <= r.status_code < 400
            txt = (r.text or "")[:150_000].lower()

            # payments
            out["payments"]["shop_pay"] = ("shop pay" in txt) or ("shop.app/pay" in txt)
            out["payments"]["apple_pay"] = ("apple pay" in txt) or ("apple-pay" in txt)
            out["payments"]["klarna"] = "klarna" in txt

            # platform heuristics
            out["platform"]["shopify"] = ("cdn.shopify.com" in txt) or ("Shopify" in r.headers.get("server",""))
            out["platform"]["bigcommerce"] = "bigcommerce" in txt
            out["platform"]["commerce"] = any(k in txt for k in ["woocommerce", "magento", "commercetools"])

            # PDP cues (homepage heuristics; best when given PDP URL, but still informative)
            out["pdp_cues"]["size_chart"] = bool(re.search(r"size\s*chart", txt))
            out["pdp_cues"]["reviews"] = "reviews" in txt or "review-count" in txt
            out["pdp_cues"]["video"] = "<video" in txt or "youtube.com/embed" in txt
    except Exception:
        pass
    out["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return out
