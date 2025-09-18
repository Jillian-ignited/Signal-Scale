# src/collectors/ecommerce_collector.py
from __future__ import annotations
import httpx, json
from typing import Dict, Any, List
from .base_collector import normalize_url

UA = {"User-Agent": "SignalScale/1.0 (+https://signal-scale.app)"}

async def _fetch_json(client: httpx.AsyncClient, url: str) -> Any:
    try:
        r = await client.get(url, headers=UA)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

async def collect_ecom_signals(url: str | None) -> Dict[str, Any]:
    """
    Shopify-friendly probe (if enabled) + minimal pricing snapshot.
    """
    url = normalize_url(url)
    out: Dict[str, Any] = {"url": url, "platform_data": {}, "pricing": {"samples": []}}
    if not url:
        return out

    origin = url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), follow_redirects=True, headers=UA) as client:
            # Shopify public products.json (often on by default; sometimes disabled)
            products = await _fetch_json(client, f"{origin}/products.json?limit=10")
            if isinstance(products, dict) and "products" in products:
                out["platform_data"]["shopify_products_count"] = len(products["products"])
                # sample prices
                for p in products["products"][:5]:
                    title = p.get("title")
                    variants = p.get("variants") or []
                    if variants:
                        price = variants[0].get("price")
                        out["pricing"]["samples"].append({"title": title, "price": price})
    except Exception:
        pass
    return out
