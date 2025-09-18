# src/analyzers/sentiment_analyzer.py
from __future__ import annotations
import os, math
from typing import List, Dict, Any

NEG = ["terrible", "bad", "hate", "awful", "slow", "broken", "late", "cheap", "worse"]
POS = ["love", "great", "good", "amazing", "fast", "premium", "quality", "best", "perfect"]

async def _simple_sentiment(texts: List[str]) -> Dict[str, Any]:
    pos = neg = 0
    for t in texts:
        tl = (t or "").lower()
        pos += sum(1 for w in POS if w in tl)
        neg += sum(1 for w in NEG if w in tl)
    total = max(1, pos + neg)
    score = round((pos - neg) / total, 3)
    return {"count": len(texts), "score": score, "pos_hits": pos, "neg_hits": neg, "method": "keyword"}

async def analyze_sentiment_batch(texts: List[str]) -> Dict[str, Any]:
    """
    Uses OPENAI_API_KEY if present (LLM summary), otherwise simple keywords.
    Keep API-free by default but upgrade gracefully.
    """
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        return await _simple_sentiment(texts)

    # Optional: LLM-based rollup (short prompt to minimize tokens)
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)
        joined = "\n".join((t or "")[:500] for t in texts[:50])  # cap
        prompt = f"Summarize overall sentiment (-1 to +1) and key themes for these brand mentions:\n\n{joined}\n\nReturn JSON: {{score: -1..1, positive_terms:[], negative_terms:[], summary:''}}"
        resp = await client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        import json
        data = json.loads(resp.choices[0].message.content)
        return {"count": len(texts), **data, "method": "openai"}
    except Exception:
        # fallback if OpenAI call fails
        return await _simple_sentiment(texts)
