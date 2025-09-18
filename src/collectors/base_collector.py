# src/collectors/base_collector.py
from __future__ import annotations
import re

def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    u = url.strip()
    if not u:
        return None
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    return u
