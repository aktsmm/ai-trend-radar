"""Static, read-only JSON API generated from data/trends.json into site/api/v1/ (GitHub Pages serves it with CORS *).

  api/v1/index.json            version, snapshot time, week list, endpoints, notes
  api/v1/latest.json           the latest week: published items (light) + candidate count
  api/v1/weeks/<week>.json     same shape, per week (only weeks that have data/reports/<week>/report.json + enrichment)
  api/v1/keywords/<id>.json    one item with digest, infographic, deck, verification checks, sources
  api/v1/categories/<cat>.json light index per category
  api/v1/candidates.json       unpublished candidates and the reasons they were skipped

python -m render.build_api
"""
import json
from datetime import datetime, timezone

from analyze import weeks as W
from collect.common import ROOT

API = ROOT / "site" / "api" / "v1"
VERSION = 1


def light(t, prefix="", self_url=True):
    eid = t["entity_id"]
    v = t.get("verification") or {}
    checked = max((c["retrieved_at"] for c in v.get("checks", [])), default=None)
    return {
        "id": eid, "keyword": t["keyword"], "headline": (t.get("slides") or [{}])[0].get("title"), "vendor": t.get("vendor"),
        "category": t["category"], "kind": t["kind"], "tags": t["tags"], "rank": t["rank"], "score": t["score"],
        "summary": (t.get("digest") or {}).get("summary", []), "published_at": t["primary"]["published_at"],
        "official_urls": t["official_urls"], "verification": {"status": v.get("status", "unverified"), "checked_at": checked},
        "urls": {**({"self": f"api/v1/keywords/{eid}.json"} if self_url else {}), "infographic": f"{prefix}assets/slides/{eid}.png",
                 "page": f"{prefix}index.html#k-{eid}"},
    }


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    data = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()
    week = data["window"]["label"]
    pub = [t for t in data["trends"] if t.get("deck")]
    cand = [t for t in data["trends"] if not t.get("deck")]
    rej = data.get("rejected_candidates", {})
    base = {"version": VERSION, "week": week, "window": data["window"], "snapshot_at": now, "data_at": data["last_successful_report_at"],
            "partial": data["window"].get("partial", False), "baseline": data["baseline"]}
    items = [light(t) for t in pub]
    dump(API / "latest.json", {**base, "count": len(items), "candidate_count": len(cand), "items": items})
    dump(API / "weeks" / f"{week}.json", {**base, "count": len(items), "candidate_count": len(cand), "items": items})
    for t in pub:
        dump(API / "keywords" / f"{t['entity_id']}.json", {**base, **light(t), "digest": t["digest"], "infographic": t["slides"][0], "deck": t["deck"],
                                                          "verification": t["verification"], "mentions": t["sources"][:5], "jp_reactions": t.get("jp_reactions", [])})
    for cat in sorted({t["category"] for t in pub}):
        dump(API / "categories" / f"{cat}.json", {**base, "category": cat, "items": [i for i, t in zip(items, pub) if t["category"] == cat]})
    dump(API / "themes.json", {**base, "note": "解釈(AI の見立て)。根拠となる項目と出典を signals / refs に示す", "items": data.get("themes", [])})
    dump(API / "highlights.json", {**base, "items": data.get("official_highlights", [])})
    dump(API / "candidates.json", {**base, "items": [{"id": t["entity_id"], "keyword": t["keyword"], "category": t["category"], "rank": t["rank"],
                                                     "status": "skipped" if t["entity_id"] in rej else "not_researched", "reason": rej.get(t["entity_id"]),
                                                     "primary_url": t["primary"]["url"]} for t in cand],
                                  "held_no_dated_source": [p["keyword"] for p in data.get("pending", [])]})
    st = data["source_status"]
    bad = sorted(k for k, v in st.items() if v.get("ok") is False)
    dump(API / "health.json", {**base, "sources": {"total": len(st), "ok": len(st) - len(bad), "failed": bad},
                              "published": len(items), "candidates": len(cand), "pending_without_primary_date": len(data.get("pending", [])),
                              "x_search_ok": bool((data.get("x_integration") or {}).get("search", {}) and data["x_integration"]["search"].get("ok"))})
    old = []
    for w, d in W.archive_weeks():
        if w == week:
            continue
        pw = [t for t in d["trends"] if t.get("deck")]
        wb = {"version": VERSION, "week": w, "window": d["window"], "snapshot_at": now, "data_at": d["last_successful_report_at"],
              "partial": False, "baseline": d["baseline"]}
        dump(API / "weeks" / f"{w}.json", {**wb, "count": len(pw), "candidate_count": len(d["trends"]) - len(pw),
                                           "items": [light(t, f"w/{w}/", False) for t in pw], "themes": d.get("themes", []),
                                           "highlights": d.get("official_highlights", [])})
        old.append((w, len(pw), d["window"]))
    weeks_info = [{"week": w, "window": win, "published": n, "url": f"api/v1/weeks/{w}.json", "page": f"w/{w}/index.html"} for w, n, win in old]
    weeks_info.append({"week": week, "window": data["window"], "published": len(pub), "url": f"api/v1/weeks/{week}.json", "page": "index.html"})
    weeks_info.sort(key=lambda x: x["week"])
    dump(API / "index.json", {
        **{k: base[k] for k in ("version", "snapshot_at", "data_at")}, "latest_week": week,
        "weeks": weeks_info,
        "endpoints": {"latest": "api/v1/latest.json", "week": "api/v1/weeks/{week}.json", "keyword": "api/v1/keywords/{id}.json",
                      "category": "api/v1/categories/{category}.json", "candidates": "api/v1/candidates.json", "highlights": "api/v1/highlights.json", "themes": "api/v1/themes.json", "health": "api/v1/health.json"},
        "downloads": {"all": "downloads/trends.json"},
        "notes": ["読み取り専用の静的 JSON です。任意条件の検索 API はありません(静的ファイルのため)。",
                  "要約・図解・ブリーフは AI の下書きを一次情報と照合したものです。ベンダー発表の数字は独自には検証していません。",
                  "週が変わると latest.json は新しい週に切り替わります。過去週は weeks/<week>.json と w/<week>/ に残ります(掲載のある週のみ)。"]})
    from xml.sax.saxutils import escape as x
    base_url = "https://aktsmm.github.io/ai-trend-radar/"
    ent = "".join(f"""<entry><id>tag:ai-trend-radar,{x(week)}:{x(t['entity_id'])}</id><title>{x(((t.get('slides') or [{}])[0].get('title') or t['keyword']))}</title>
<link href="{base_url}index.html#k-{x(t['entity_id'])}"/><updated>{x(t['primary']['published_at'] or data['last_successful_report_at'])}</updated>
<category term="{x(t['category'])}"/><summary>{x(' '.join(t['digest']['summary']))}</summary></entry>\n""" for t in pub)
    (ROOT / "site" / "feed.xml").write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><id>tag:ai-trend-radar,feed</id><title>AI Trend Radar {x(week)}</title><link rel="self" href="{base_url}feed.xml"/>
<updated>{x(now)}</updated>\n{ent}</feed>\n""", encoding="utf-8")
    print("API ->", API, f"({len(items)} items)")


if __name__ == "__main__":
    main()
