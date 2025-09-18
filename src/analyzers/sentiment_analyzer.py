# src/analyzers/sentiment_analyzer.py
from __future__ import annotations
import os, json
from typing import List, Dict, Any

NEG = ["terrible","bad","hate","awful","slow","broken","late","cheap","worse"]
POS = ["love","great","good","amazing","fast","premium","quality","best","perfect"]

async def _simple(texts: List[str]) -> Dict[str, Any]:
    if not texts:
        return {"count": 0, "score": 0.0, "pos_hits": 0, "neg_hits": 0, "method": "none"}
    pos = neg = 0
    for t in texts:
        tl = (t or "").lower()
        pos += sum(1 for w in POS if w in tl)
        neg += sum(1 for w in NEG if w in tl)
    total = max(1, pos + neg)
    score = round((pos - neg) / total, 3)
    return {"count": len(texts), "score": score, "pos_hits": pos, "neg_hits": neg, "method": "keyword"}

async def analyze_sentiment_batch(texts: List[str]) -> Dict[str, Any]:
    if not texts:
        return await _simple(texts)

    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        return await _simple(texts)

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)
        joined = "\n".join((t or "")[:500] for t in texts[:60])
        prompt = (
            "Summarize overall sentiment (-1..+1) and key terms for these brand mentions. "
            "Return strict JSON: {score: number, positive_terms:[], negative_terms:[], summary:''}\n\n"
            f"{joined}"
        )
        resp = await client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            response_format={"type":"json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return {"count": len(texts), **data, "method": "openai"}
    except Exception:
        return await _simple(texts)
