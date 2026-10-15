"""Write .work/pending.json: the next candidates the digest workflow should research.

python -m analyze.pending --week 2026-W42 [--limit 8]

Output is UNTRUSTED data for the agent (titles/descriptions come from the open web). Candidates already published or
already rejected for this week are skipped. The agent may only research what is listed here.
"""
import argparse
import json

from collect.common import ROOT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--limit", type=int, default=8)
    a = ap.parse_args()
    wk = ROOT / "data" / "reports" / a.week
    data = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
    done = set()
    for f in ("enrichment.json",):
        p = wk / f
        if p.exists():
            done |= set(json.loads(p.read_text(encoding="utf-8"))["entities"])
    p = wk / "rejected_candidates.json"
    if p.exists():
        done |= set(json.loads(p.read_text(encoding="utf-8")))
    out = []
    for t in data["trends"]:
        if t["entity_id"] in done or t.get("deck"):
            continue
        out.append({"entity_id": t["entity_id"], "keyword": t["keyword"], "rank": t["rank"], "category": t["category"], "vendor": t.get("vendor"),
                    "primary": {"url": t["primary"]["url"], "title": t["primary"]["title"], "published_at": t["primary"]["published_at"],
                                "source_type": t["primary"]["source_type"]},
                    "mentions": [{"source": s["name"], "title": s["title"], "url": s["url"]} for s in t["sources"][:5]]})
        if len(out) >= a.limit:
            break
    work = ROOT / ".work"
    work.mkdir(exist_ok=True)
    (work / "pending.json").write_text(json.dumps({"week": a.week, "window": data["window"], "candidates": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), "pending candidates ->", work / "pending.json")


if __name__ == "__main__":
    main()
