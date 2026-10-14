"""X (Twitter) integration: status URLs found in other sources + Brave site:x.com discovery, enriched via FxTwitter.

FxTwitter search (/2/search) is 404, so it is only used for known status URLs. No credentials are sent to it.
X metrics are an auxiliary signal; adoption is decided from body text and linked repo/official pages.
"""
import json
import os
import re
import urllib.parse as up
from concurrent.futures import ThreadPoolExecutor

from .common import RAW, X_URL_RE, extract_x_urls, get_json, strip_html

CACHE = RAW / "x_posts.json"


def fetch_status(user, sid):
    """FxTwitter v2, falling back to the v1 shape. Returns normalized dict or None."""
    for url in (f"https://api.fxtwitter.com/2/status/{sid}", f"https://api.fxtwitter.com/{user}/status/{sid}"):
        try:
            j = get_json(url, timeout=15, retries=0)
        except Exception:
            continue
        t = j.get("status") or j.get("tweet")
        if not t:
            continue
        a = t.get("author") or {}
        return {"id": sid, "url": f"https://x.com/{a.get('screen_name') or user}/status/{sid}",
                "author": a.get("screen_name") or user, "text": t.get("text") or (t.get("raw_text") or {}).get("text", ""),
                "likes": t.get("likes", 0) or 0, "reposts": t.get("reposts") or t.get("retweets", 0) or 0,
                "views": t.get("views") or 0, "created": t.get("created_at"),
                "links": [e.get("url") for e in ((t.get("raw_text") or {}).get("facets") or []) if e.get("url")]}
    return None


def collect_links(items):
    """Map x status URL -> list of source item indexes mentioning it."""
    found = {}
    for idx, it in enumerate(items):
        for u in extract_x_urls(it.get("url"), it.get("text"), it.get("raw_html"), " ".join(it.get("links") or [])):
            found.setdefault(u, []).append(idx)
    return found


def brave_search(keyword):
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        return None
    q = f"site:x.com {keyword} (LLM OR ollama OR local)"
    url = "https://api.search.brave.com/res/v1/web/search?" + up.urlencode({"q": q, "freshness": "pw", "count": 10})
    r = get_json(url, {"X-Subscription-Token": key, "Accept": "application/json"})
    return [x["url"] for x in (r.get("web") or {}).get("results", []) if X_URL_RE.search(x.get("url", ""))]


def enrich(urls, workers=6):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = []
    for u in urls:
        m = X_URL_RE.search(u)
        if m and m.group(2) not in cache:
            todo.append((m.group(1), m.group(2)))
    with ThreadPoolExecutor(workers) as ex:
        for (user, sid), res in zip(todo, ex.map(lambda p: fetch_status(*p), todo)):
            cache[sid] = res or {"id": sid, "failed": True, "url": f"https://x.com/{user}/status/{sid}"}
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache
