"""Run all collectors independently; save data/raw/<source>.json, ledger/status, X watchlist and a light daily snapshot.

data/raw and data/snapshots are NOT committed (CI uploads them as artifacts); weekly reports under data/reports are.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import jp, official, x_watch
from .common import NOW, RAW, ROOT, save_raw
from .sources import SOURCES

SEMANTICS = {  # how a metric may be interpreted across days
    "github_new": "total_stars (diffable per repo)", "github_trending": "weekly_stars (explicit, from trending page)",
    "hf_models": "trendingScore (rank observation only)", "hf_spaces": "trendingScore (rank observation only)",
    "hf_papers": "upvotes (rank observation only)", "hackernews": "points (diffable per story)",
    "openrouter": "event (model created)", "official": "event (announcement)", "gh_releases": "event (release)",
}


def run_one(name):
    fn, group = SOURCES[name]
    if fn is None:
        return name, None
    t = time.time()
    try:
        items = fn()
        save_raw(name, items)
        return name, {"ok": True, "count": len(items), "group": group, "seconds": round(time.time() - t, 1)}
    except Exception as e:
        return name, {"ok": False, "error": f"{type(e).__name__}: {e}"[:300], "group": group}


def run_official(status):
    try:
        off, rel, ledger = official.collect_all()
        save_raw("official", off)
        save_raw("gh_releases", rel)
        save_raw("_official_ledger", ledger)
        status["official"] = {"ok": True, "count": len(off), "group": "vendor"}
        status["gh_releases"] = {"ok": True, "count": len(rel), "group": "tools"}
    except Exception as e:
        save_raw("official", [])
        save_raw("gh_releases", [])
        status["official"] = status["gh_releases"] = {"ok": False, "error": str(e)[:200], "group": "vendor"}


def run_jp(status):
    try:
        items, st = jp.collect_jp()
        save_raw("jp_reaction", items)
        status["jp_reaction"] = {"ok": any(s["ok"] for s in st.values()), "count": len(items), "group": "community-ja", "feeds": st}
    except Exception as e:
        save_raw("jp_reaction", [])
        status["jp_reaction"] = {"ok": False, "error": str(e)[:200], "group": "community-ja"}


def run_x(status):
    search = x_watch.probe_search()
    try:
        posts, wstat = x_watch.collect_watchlist()
        save_raw("x_watch", posts)
        status["x_watch"] = {"ok": any(s["ok"] for s in wstat.values()), "count": len(posts), "group": "community", "accounts": wstat}
    except Exception as e:
        save_raw("x_watch", [])
        status["x_watch"] = {"ok": False, "error": str(e)[:200], "group": "community"}
    status["x_search"] = {"ok": search["ok"], "note": search["status"], "group": "community"}


def snapshot():
    snap = {"date": NOW.strftime("%Y-%m-%d"), "observed_at": NOW.isoformat(), "sources": {}}
    for name, sem in SEMANTICS.items():
        f = RAW / f"{name}.json"
        if not f.exists():
            continue
        rows = json.loads(f.read_text(encoding="utf-8"))
        snap["sources"][name] = {"metric_semantics": sem, "items": [
            {"id": r["title"], "rank": r.get("rank") or i + 1, "metric": r["metric"]} for i, r in enumerate(rows)]}
    d = ROOT / "data" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{snap['date']}.json").write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")


def main():
    status = {}
    with ThreadPoolExecutor(6) as ex:
        for name, st in ex.map(run_one, SOURCES):
            if st is not None:
                status[name] = st
                print(name, st)
    run_official(status)
    run_x(status)
    run_jp(status)
    print({k: v.get("ok") for k, v in status.items()})
    save_raw("_status", {"collected_at": datetime.now(timezone.utc).isoformat(), "sources": status})
    snapshot()


if __name__ == "__main__":
    main()
