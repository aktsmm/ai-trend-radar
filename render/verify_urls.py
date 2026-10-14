"""GET-check every official/evidence URL used by the enrichment and slides; writes url_checks into enrichment.json.

python -m render.verify_urls [--week 2026-W42]
"""
import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

from collect.common import ROOT, UA


def status_of(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"error: {type(e).__name__}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default="2026-W42")
    a = ap.parse_args()
    d = ROOT / "data" / "reports" / a.week
    enr = json.loads((d / "enrichment.json").read_text(encoding="utf-8"))
    slides = json.loads((d / "slides.json").read_text(encoding="utf-8"))
    urls = set()
    for eid, e in enr["entities"].items():
        urls |= set(e["official_urls"])
        for c in e["checks"]:
            urls |= set(c["evidence_urls"])
        urls |= {s["official_url"] for s in slides.get(eid, [])}
    now = datetime.now(timezone.utc).isoformat()
    enr["url_checks"] = {u: {"status": status_of(u), "checked_at": now} for u in sorted(urls)}
    (d / "enrichment.json").write_text(json.dumps(enr, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = {u: c["status"] for u, c in enr["url_checks"].items() if c["status"] != 200}
    print(f"{len(urls) - len(bad)}/{len(urls)} OK;", "non-200:", bad or "none")


if __name__ == "__main__":
    main()
