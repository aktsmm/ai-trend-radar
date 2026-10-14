"""X as an *entry point* for official announcements.

- /2/search is probed once per run (404 since 2026-10-09: upstream X change, FxEmbed issue #2303) and skipped for a cooldown.
- Watchlist accounts (config/x_watchlist.yml, owner-verified official/key-person handles) are read via /2/profile/{h}/statuses.
Adoption of any candidate still requires an official site / release note / GitHub Release (see analyze/report.py).
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import yaml

from .common import NOW, RAW, ROOT, SINCE, get_json
from .x import X_URL_RE

STATE = RAW / "_x_state.json"
COOLDOWN_S = 6 * 3600


def _state():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def probe_search():
    st = _state()
    last = st.get("search_404_at")
    if last and time.time() - last < COOLDOWN_S:
        return {"status": "skipped (cooldown after 404)", "ok": False}
    try:
        get_json("https://api.fxtwitter.com/2/search?q=llm&feed=latest&count=1", timeout=15, retries=0)
        st.pop("search_404_at", None)
        res = {"status": "ok", "ok": True}
    except Exception as e:
        st["search_404_at"] = time.time()
        res = {"status": f"unavailable: {e}"[:120], "ok": False}
    RAW.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st), encoding="utf-8")
    return res


def _links(t):
    rt = t.get("raw_text") or {}
    urls = [f.get("replacement") or f.get("original") or f.get("display") for f in (rt.get("facets") or []) if f.get("type") == "url"]
    return [u for u in urls if u and u.startswith("http")]


def fetch_handle(handle, since_id=None):
    try:
        j = get_json(f"https://api.fxtwitter.com/2/profile/{handle}/statuses", timeout=20, retries=1)
    except Exception as e:
        return handle, None, f"{type(e).__name__}: {e}"[:120]
    out = []
    for t in j.get("results", []):
        if t.get("replying_to") or t.get("reposted_by") or (t.get("text") or "").startswith("RT @"):
            continue
        created = datetime.strptime(t["created_at"], "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc)
        if created < SINCE:
            continue
        out.append({"id": t["id"], "url": t["url"], "author": handle, "text": t.get("text", ""), "created": created.isoformat(),
                    "likes": t.get("likes") or 0, "reposts": t.get("reposts") or 0, "views": t.get("views") or 0,
                    "links": _links(t)})
    return handle, out, None


def collect_watchlist():
    cfg = yaml.safe_load((ROOT / "config" / "x_watchlist.yml").read_text(encoding="utf-8"))
    handles = [a["handle"] for a in cfg["accounts"]]
    st = _state()
    last_ids = st.get("last_ids", {})
    posts, status = [], {}
    with ThreadPoolExecutor(5) as ex:
        for h, res, err in ex.map(lambda h: fetch_handle(h, last_ids.get(h)), handles):
            if res is None:
                status[h] = {"ok": False, "error": err}
                continue
            status[h] = {"ok": True, "posts": len(res)}
            posts += res
            if res:
                last_ids[h] = max(res, key=lambda p: int(p["id"]))["id"]
    st["last_ids"] = last_ids
    STATE.write_text(json.dumps(st), encoding="utf-8")
    return posts, status
