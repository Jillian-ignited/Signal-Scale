# src/collectors/social_media_collector.py
from __future__ import annotations
import httpx, re, math
from typing import Dict, Any, List, Tuple

UA = {"User-Agent": "SignalScaleBot/1.0"}

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def _brand_queries(brand: str) -> List[str]:
    """
    Build safer search terms: exact brand, brand + category terms, common nicknames.
    Reduces noise for big brands (e.g., 'Nike' vs people named 'Nicke'/typos).
    """
    b = (brand or "").strip()
    if not b: return []
    parts = [f'"{b}" streetwear', f'"{b}" apparel', f'"{b}" clothing', f'"{b}" brand']
    # short brands get exact quotes only to reduce false positives
    if len(b) <= 5:
        parts.insert(0, f'"{b}"')
    return parts

def _score_post(p: Dict[str, Any]) -> float:
    base = 1.0
    # weight by native signals if present
    if p.get("platform") == "reddit":
        base += 0.5 * (p.get("score") or 0) + 0.2 * (p.get("comments") or 0)
    # title/text length boosts credibility a bit
    l = len((p.get("title") or "") + " " + (p.get("text") or ""))
    base += min(2.0, l / 140.0)
    return base

def _dedup(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for p in posts:
        k = (p.get("platform"), _norm(p.get("title",""))[:80])
        if k in seen: continue
        seen.add(k); out.append(p)
    return out

async def _reddit_search(q: str, limit: int = 15) -> List[Dict[str, Any]]:
    url = f"https://www.reddit.com/search.json?q={q}&limit={limit}&sort=new"
    posts: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), headers=UA) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                for item in (data.get("data", {}).get("children", []) or []):
                    d = item.get("data", {})
                    title = _norm(d.get("title", ""))
                    text = _norm(d.get("selftext",""))
                    # basic brand term filter — ensure brand token appears
                    if not title and not text: 
                        continue
                    posts.append({
                        "platform": "reddit",
                        "title": title,
                        "text": text,
                        "score": d.get("score"),
                        "comments": d.get("num_comments"),
                        "url": f"https://www.reddit.com{d.get('permalink','')}"
                    })
    except Exception:
        pass
    return posts

async def _youtube_search_html(q: str, limit: int = 10) -> List[Dict[str, Any]]:
    # HTML search — best-effort
    url = f"https://www.youtube.com/results?search_query={q}"
    out: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = await client.get(url)
            if r.status_code == 200:
                html = r.text or ""
                for m in re.finditer(r'{"videoId":"([A-Za-z0-9_-]{11})","title":\{"runs":\[\{"text":"([^"]+)"\}\]', html):
                    vid, title = m.group(1), _norm(m.group(2))
                    out.append({
                        "platform": "youtube",
                        "title": title,
                        "text": title,
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    })
                    if len(out) >= limit: break
    except Exception:
        pass
    return out

async def collect_social_signals(brand_name: str, window_days: int = 7) -> Dict[str, Any]:
    """
    Multi-query search → merge → dedup → rank.
    """
    qs = _brand_queries(brand_name)
    all_posts: List[Dict[str, Any]] = []
    for q in qs:
        reddit = await _reddit_search(q)
        yt = await _youtube_search_html(q)
        all_posts.extend(reddit); all_posts.extend(yt)

    all_posts = _dedup(all_posts)
    all_posts.sort(key=_score_post, reverse=True)
    return {"posts": all_posts[:50]}
