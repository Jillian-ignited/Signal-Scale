# src/collectors/social_media_collector.py
from __future__ import annotations
import os, re, datetime as dt, httpx
from typing import Dict, Any, List

UA = {"User-Agent": "SignalScaleBot/1.0 (+https://signal-scale.app)"}
YOUTUBE_API_KEY = (os.environ.get("YOUTUBE_API_KEY") or "").strip()
YOUTUBE_REGION  = (os.environ.get("YOUTUBE_REGION") or "US").strip().upper()
YOUTUBE_MAX_DAYS = int(os.environ.get("YOUTUBE_MAX_DAYS", "30"))

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def _brand_queries(brand: str) -> List[str]:
    b = (brand or "").strip()
    if not b: return []
    qs = [
        f'"{b}" apparel', f'"{b}" brand', f'"{b}" clothing',
        f'"{b}" streetwear', f'"{b}" drop', f'"{b}" collab',
        f'"{b}" unboxing', f'"{b}" review'
    ]
    if len(b) <= 5:
        qs.insert(0, f'"{b}"')
    return qs

# --------- Reddit ---------
async def _reddit_search(q: str, limit: int = 20) -> List[Dict[str, Any]]:
    url = f"https://www.reddit.com/search.json?q={q}&limit={limit}&sort=new"
    out: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), headers=UA, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                for item in (data.get("data", {}).get("children", []) or []):
                    d = item.get("data", {})
                    title = _norm(d.get("title", "")); text = _norm(d.get("selftext", ""))
                    if not title and not text: continue
                    out.append({
                        "platform": "reddit", "title": title, "text": text,
                        "score": d.get("score"), "comments": d.get("num_comments"),
                        "url": f"https://www.reddit.com{d.get('permalink','')}"
                    })
    except Exception:
        pass
    return out

# --------- YouTube (API preferred) ---------
def _iso_after(days: int) -> str:
    after = dt.datetime.utcnow() - dt.timedelta(days=max(1, days))
    return after.replace(microsecond=0).isoformat("T") + "Z"

async def _yt_api_search(query: str, max_results: int = 18) -> List[Dict[str, Any]]:
    if not YOUTUBE_API_KEY:
        return []
    base = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": YOUTUBE_API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": str(min(50, max_results)),
        "regionCode": YOUTUBE_REGION,
        "order": "date",
        "publishedAfter": _iso_after(YOUTUBE_MAX_DAYS),
        "safeSearch": "none",
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0)) as client:
            r = await client.get(base, params=params)
            if r.status_code != 200:
                return []
            items = (r.json().get("items") or [])
            out = []
            for it in items:
                vid = (it.get("id") or {}).get("videoId")
                sn  = (it.get("snippet") or {})
                if not vid: continue
                title = _norm(sn.get("title")); desc = _norm(sn.get("description"))
                published = sn.get("publishedAt")
                out.append({"videoId": vid, "title": title, "description": desc, "publishedAt": published})
            return out
    except Exception:
        return []

async def _yt_api_video_stats(video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    if not (YOUTUBE_API_KEY and video_ids):
        return {}
    base = "https://www.googleapis.com/youtube/v3/videos"
    params = {"key": YOUTUBE_API_KEY, "part": "statistics", "id": ",".join(video_ids[:50])}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0)) as client:
            r = await client.get(base, params=params)
            if r.status_code != 200:
                return {}
            stats: Dict[str, Dict[str, Any]] = {}
            for it in (r.json().get("items") or []):
                vid = it.get("id"); st = (it.get("statistics") or {})
                stats[vid] = {
                    "viewCount": int(st.get("viewCount", 0)),
                    "likeCount": int(st.get("likeCount", 0)) if "likeCount" in st else None,
                    "commentCount": int(st.get("commentCount", 0)) if "commentCount" in st else None,
                }
            return stats
    except Exception:
        return {}

async def _youtube_search_html(q: str, limit: int = 10) -> List[Dict[str, Any]]:
    url = f"https://www.youtube.com/results?search_query={q}"
    out: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code == 200:
                html = r.text or ""
                for m in re.finditer(r'{"videoId":"([A-Za-z0-9_-]{11})","title":\{"runs":\[\{"text":"([^"]+)"\}\]', html):
                    vid, title = m.group(1), _norm(m.group(2))
                    out.append({"videoId": vid, "title": title, "description": title, "publishedAt": None})
                    if len(out) >= limit: break
    except Exception:
        pass
    return out

async def _youtube_posts(q: str, limit: int = 12) -> List[Dict[str, Any]]:
    vids = await (_yt_api_search(q, max_results=limit) if YOUTUBE_API_KEY else _yt_api_search(q, max_results=0))
    if not vids and not YOUTUBE_API_KEY:
        vids = await _youtube_search_html(q, limit=limit)

    ids = [v["videoId"] for v in vids if v.get("videoId")]
    stats = await _yt_api_video_stats(ids) if ids else {}

    out = []
    for v in vids:
        vid = v.get("videoId")
        st  = stats.get(vid, {})
        out.append({
            "platform": "youtube",
            "title": v.get("title"),
            "text": v.get("description") or v.get("title"),
            "url": f"https://www.youtube.com/watch?v={vid}" if vid else None,
            "views": st.get("viewCount"),
            "likes": st.get("likeCount"),
            "comments": st.get("commentCount"),
            "publishedAt": v.get("publishedAt")
        })
    return out

# --------- Rank / Dedup / Public API ---------
def _score_post(p: Dict[str, Any]) -> float:
    base = 1.0
    if p.get("platform") == "reddit":
        base += 0.4 * (p.get("score") or 0) + 0.2 * (p.get("comments") or 0)
    if p.get("platform") == "youtube":
        base += 0.000002 * (p.get("views") or 0) + 0.01 * (p.get("likes") or 0 or 0)
    l = len((p.get("title") or "") + " " + (p.get("text") or ""))
    base += min(2.0, l / 160.0)
    return base

def _dedup(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for p in posts:
        k = (p.get("platform"), _norm(p.get("title",""))[:120])
        if k in seen: continue
        seen.add(k); out.append(p)
    return out

async def collect_social_signals(brand_name: str, window_days: int = 7) -> Dict[str, Any]:
    qs = _brand_queries(brand_name)
    all_posts: List[Dict[str, Any]] = []
    for q in qs:
        all_posts.extend(await _reddit_search(q))
        all_posts.extend(await _youtube_posts(q))

    all_posts = _dedup(all_posts)
    all_posts.sort(key=_score_post, reverse=True)
    return {"posts": all_posts[:80], "meta": {"youtube_api": bool(YOUTUBE_API_KEY), "region": YOUTUBE_REGION, "days": YOUTUBE_MAX_DAYS}}
