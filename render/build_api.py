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

from collect.common import ROOT

API = ROOT / "site" / "api" / "v1"
VERSION = 1


def light(t):
    eid = t["entity_id"]
    v = t.get("verification") or {}
    checked = max((c["retrieved_at"] for c in v.get("checks", [])), default=None)
    return {
        "id": eid, "keyword": t["keyword"], "headline": (t.get("slides") or [{}])[0].get("title"), "vendor": t.get("vendor"),
        "category": t["category"], "kind": t["kind"], "tags": t["tags"], "rank": t["rank"], "score": t["score"],
        "summary": (t.get("digest") or {}).get("summary", []), "published_at": t["primary"]["published_at"],
        "official_urls": t["official_urls"], "verification": {"status": v.get("status", "unverified"), "checked_at": checked},
        "urls": {"self": f"api/v1/keywords/{eid}.json", "infographic": f"assets/slides/{eid}.png",
                 "pdf": f"downloads/{eid}.pdf", "pptx": f"downloads/{eid}.pptx", "page": f"index.html#k-{eid}"},
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
    dump(API / "candidates.json", {**base, "items": [{"id": t["entity_id"], "keyword": t["keyword"], "category": t["category"], "rank": t["rank"],
                                                     "status": "skipped" if t["entity_id"] in rej else "unverified", "reason": rej.get(t["entity_id"]),
                                                     "primary_url": t["primary"]["url"]} for t in cand]})
    st = data["source_status"]
    bad = sorted(k for k, v in st.items() if v.get("ok") is False)
    dump(API / "health.json", {**base, "sources": {"total": len(st), "ok": len(st) - len(bad), "failed": bad},
                              "published": len(items), "candidates": len(cand), "pending_without_primary_date": len(data.get("pending", [])),
                              "x_search_ok": bool((data.get("x_integration") or {}).get("search", {}) and data["x_integration"]["search"].get("ok"))})
    weeks = sorted(p.name for p in (ROOT / "data" / "reports").iterdir() if (p / "report.json").exists())
    dump(API / "index.json", {
        **{k: base[k] for k in ("version", "snapshot_at", "data_at")}, "latest_week": week,
        "weeks": [{"week": w, "published": len(pub) if w == week else None, "url": f"api/v1/weeks/{w}.json" if w == week else None} for w in weeks],
        "endpoints": {"latest": "api/v1/latest.json", "week": "api/v1/weeks/{week}.json", "keyword": "api/v1/keywords/{id}.json",
                      "category": "api/v1/categories/{category}.json", "candidates": "api/v1/candidates.json", "health": "api/v1/health.json"},
        "downloads": {"pdf": "downloads/{id}.pdf", "pptx": "downloads/{id}.pptx", "weekly_pdf": f"downloads/weekly-{week}.pdf",
                      "weekly_pptx": f"downloads/weekly-{week}.pptx", "all": "downloads/trends.json"},
        "notes": ["読み取り専用の静的 JSON です。任意条件の検索 API はありません(静的ファイルのため)。",
                  "要約・図解・ブリーフは AI の下書きを一次情報と照合したものです。ベンダー発表の数字は独自には検証していません。",
                  "週が変わると latest.json は新しい週に切り替わります。過去週は weeks/<week>.json(データがある週のみ)。"]})
    print("API ->", API, f"({len(items)} items)")


if __name__ == "__main__":
    main()
