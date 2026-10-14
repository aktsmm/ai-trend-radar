"""Run all collectors in parallel; save data/raw/<source>.json and data/raw/_status.json."""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .common import save_raw
from .sources import SOURCES


def run_one(name):
    fn, group = SOURCES[name]
    t = time.time()
    try:
        items = fn()
        save_raw(name, items)
        return name, {"ok": True, "count": len(items), "group": group, "seconds": round(time.time() - t, 1)}
    except Exception as e:
        return name, {"ok": False, "error": f"{type(e).__name__}: {e}"[:300], "group": group}


def main():
    status = {}
    with ThreadPoolExecutor(6) as ex:
        for name, st in ex.map(run_one, SOURCES):
            status[name] = st
            print(name, st)
    save_raw("_status", {"collected_at": datetime.now(timezone.utc).isoformat(), "sources": status})


if __name__ == "__main__":
    main()
