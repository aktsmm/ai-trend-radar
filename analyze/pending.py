"""Write .work/pending.json: the next candidates the digest workflow should research.

python -m analyze.pending --week 2026-W42 [--limit 8]

Output is UNTRUSTED data for the agent (titles/descriptions come from the open web). Candidates already published or
already rejected for this week are skipped. The agent may only research what is listed here.
"""
import argparse
import json

from collect.common import ROOT


def vendor_links(t, limit=2):
    """Links in this candidate's mentions that point at an allowlisted first-party domain, other than the primary page.

    A model that ranks via a catalog page (e.g. OpenRouter) is often discussed on HN / Reddit with a link to the vendor's own announcement; that link is
    the page to research. Only allowlisted vendor domains qualify, so an arbitrary link in a post is never fetched.
    """
    from urllib.parse import urlparse

    from analyze.report import OFFICIAL_DOMAINS
    seen, out = {t["primary"]["url"]}, []
    for s in t["sources"]:
        u = s["url"]
        host = urlparse(u).netloc.lower().removeprefix("www.")
        if u not in seen and u.startswith("https://") and any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS) and "huggingface.co" not in host:
            seen.add(u)
            out.append(u)
    return out[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    ap.add_argument("--limit", type=int, default=8)
    a = ap.parse_args()
    data = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
    a.week = a.week or data["window"]["label"]
    wk = ROOT / "data" / "reports" / a.week
    done = set()
    for f in ("enrichment.json",):
        p = wk / f
        if p.exists():
            done |= set(json.loads(p.read_text(encoding="utf-8"))["entities"])
    p = wk / "rejected_candidates.json"
    if p.exists():
        done |= set(json.loads(p.read_text(encoding="utf-8")))
    out = []
    # Notable launches first: a model / release backed by a first-party source (official feed, release, HF model card) goes ahead of rank order,
    # so a big announcement that ranks 7th is not left for a later run behind tools and repos.
    first_party = {"announcement", "release_note", "model_card", "docs", "product_page"}
    todo = [t for t in data["trends"] if t["entity_id"] not in done and not t.get("deck")]
    todo.sort(key=lambda t: (0 if t["kind"] == "model" and t["primary"]["source_type"] in first_party else 1, t["rank"]))
    for t in todo:
        out.append({"entity_id": t["entity_id"], "keyword": t["keyword"], "rank": t["rank"], "category": t["category"], "vendor": t.get("vendor"),
                    "primary": {"url": t["primary"]["url"], "title": t["primary"]["title"], "published_at": t["primary"]["published_at"],
                                "source_type": t["primary"]["source_type"]},
                    "mentions": [{"source": s["name"], "title": s["title"], "url": s["url"]} for s in t["sources"][:5]],
                    "vendor_links": vendor_links(t)})
        if len(out) >= a.limit:
            break
    work = ROOT / ".work"
    work.mkdir(exist_ok=True)
    (work / "pending.json").write_text(json.dumps({"week": a.week, "window": data["window"], "candidates": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), "pending candidates ->", work / "pending.json")


if __name__ == "__main__":
    main()
