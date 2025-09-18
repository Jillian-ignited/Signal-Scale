# src/analyzers/trend_analyzer.py
from __future__ import annotations
import re
from typing import List, Dict, Any
HASHTAG_RE = re.compile(r"(#\w+)")
WORD_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9\-]{2,})\b")

def extract_trends(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts = {}
    for p in posts:
        txt = f"{p.get('title','')} {p.get('text','')}"
        for h in HASHTAG_RE.findall(txt):
            counts[h.lower()] = counts.get(h.lower(), 0) + 1
        # also collect notable words (very naive)
        for w in WORD_RE.findall(txt):
            if len(w) > 3 and w.lower() not in {"https", "www", "http"}:
                counts[w.lower()] = counts.get(w.lower(), 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    out = [{"term": k, "count": v} for k,v in ranked[:30]]
    return out
