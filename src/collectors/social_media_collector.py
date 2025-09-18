# src/collectors/social_media_collector.py
from __future__ import annotations
import httpx, re
from typing import Dict, Any, List

UA = {"User-Agent": "SignalScaleBot/1.0"}

def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", (txt or "")).strip()

async def _reddit_search(q: str, limit: int = 20) -> List[Dict[str, Any]]:
    url = f"https://www.reddit.com/search.json?q={q}&limit={limit}&sort=new"
    posts: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), headers=UA) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                for item in (data.get("data", {}).get("children", []) or []):
                    d = item.get("data", {})
                    posts.append({
                        "platform": "reddit",
                        "title": _clean(d.get("title", "")),
                        "text": _clean(d.get("selftext", "")),
                        "score": d.get("score"),
                        "comments": d.get("num_comments"),
                        "url": f"https://www.reddit.com{d.get('permalink', '')}"
                    })
    except Exception:
        pass
    return posts

async def _youtube_search(q: str, limit: int = 10) -> List[Dict[str, Any]]:
    # lightweight HTML scrape (no API key); best-effort
    url = f"https://www.youtube.com/results?search_query={q}"
    posts: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = await client.get(url)
            if r.status_code == 200:
                html = r.text or ""
                # crude extract of video titles/ids
                for m in re.finditer(r'{"videoId":"([A-Za-z0-9_-]{11})","title":\{"runs":\[\{"text":"([^"]+)"\}\]', html):
                    vid, title = m.group(1), m.group(2)
                    posts.append({
                        "platform": "youtube",
                        "title": _clean(title),
                        "text": _clean(title),
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    })
                    if len(posts) >= limit:
                        break
    except Exception:
        pass
    return posts

async def collect_social_signals(brand_name: str, window_days: int = 7) -> Dict[str, Any]:
    q = (brand_name or "").strip()
    if not q:
        return {"posts": []}
    q_enc = q.replace(" ", "+")
    reddit, yt = await _reddit_search(q_enc), await _youtube_search(q_enc)
    return {"posts": reddit + yt}
