"""Weekly "GitHub 急上昇 AI repo" report file: data/reports/<week>/github_top.json (committed, trusted-code output).

python -m analyze.github_top [--week 2026-W45]    # raw data/raw/github_weekly.json -> report file (kept as is when raw is missing)

One-liners (`one_liner`) written by the digest for a repo are carried over; everything else is deterministic.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone

from collect.common import RAW, ROOT

TOP = 10
TAGS = {"coding-agent": "コーディング支援・エージェント", "infra": "実行基盤・推論", "data": "データ・検索・知識", "learning": "学習・教材",
        "media": "画像・動画・デザイン", "tools": "その他のツール"}
TAG_RULES = [("learning", r"tutorial|course|learn|cookbook|awesome|examples?|hub\b|guide"),
             ("coding-agent", r"agent|claude|codex|cursor|copilot|skills?|mcp|coding|orchestrat"),
             ("data", r"rag\b|ontology|embedding|vector|knowledge|memory|retriev|database|scrap|crawl"),
             ("infra", r"inference|gpu|serving|runtime|llama\.cpp|ollama|vllm|quantiz|deploy|router|gateway|proxy"),
             ("media", r"video|image|diffusion|design|music|audio|speech")]
REPO_URL = re.compile(r"^https://github\.com/[\w.\-]+/[\w.\-]+$")


def tag_of(item):
    text = " ".join([item["repo"], item.get("description", ""), " ".join(item.get("topics", []))]).lower()
    for tag, pattern in TAG_RULES:
        if re.search(pattern, text):
            return tag
    return "tools"


def problems(report):
    out = []
    items = report.get("items", [])
    if not items:
        out.append("no items")
    for i, it in enumerate(items, 1):
        who = it.get("repo", f"#{i}")
        if it.get("rank") != i:
            out.append(f"{who}: rank must be {i}")
        if not REPO_URL.match(it.get("url", "")) or it["url"] != f"https://github.com/{it.get('repo')}":
            out.append(f"{who}: url must be https://github.com/<repo>")
        if not isinstance(it.get("stars_week"), int) or it["stars_week"] <= 0:
            out.append(f"{who}: stars_week must be a positive integer")
        if i > 1 and it.get("stars_week", 0) > items[i - 2].get("stars_week", 0):
            out.append(f"{who}: not sorted by stars_week")
        if it.get("tag") not in TAGS:
            out.append(f"{who}: unknown tag")
        if len(it.get("one_liner") or "") > 80:
            out.append(f"{who}: one_liner over 80 chars")
    if len({it.get("repo") for it in items}) != len(items):
        out.append("duplicate repo")
    return out


def build(raw, week, previous=None, now=None):
    now = now or datetime.now(timezone.utc)
    kept = {it["repo"]: it.get("one_liner") for it in (previous or {}).get("items", []) if it.get("one_liner")}
    items = []
    for i, it in enumerate(raw["items"][:TOP], 1):
        row = {"rank": i, "repo": it["repo"], "url": it["url"], "stars_week": int(it["stars_week"]), "stars_total": it.get("stars_total"),
               "language": it.get("language"), "topics": it.get("topics", []), "description": (it.get("description") or "")[:200],
               "one_liner": kept.get(it["repo"])}
        row["tag"] = tag_of(row)
        items.append(row)
    return {"week": week, "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "metric": "stars gained this week (github.com/trending, AI-filtered)",
            "pages_ok": raw.get("pages_ok"), "pages_total": raw.get("pages_total"), "excluded_count": len(raw.get("excluded", [])), "items": items}


SINGLE_CARDS = 3     # the top repos each get their own card on the digest
GROUP_MAX = 3        # the rest are bundled by field, at most this many repos per card
GROUP_LABEL = {"coding-agent": "コーディング支援・エージェント", "infra": "実行基盤・推論", "data": "データ・検索・知識", "learning": "学習・教材",
               "media": "画像・動画・デザイン", "tools": "その他のツール"}


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _chunks(items):
    """Balanced chunks of at most GROUP_MAX (4 -> 2+2, 5 -> 3+2)."""
    k = -(-len(items) // GROUP_MAX)
    size, extra, out, i = len(items) // k, len(items) % k, [], 0
    for n in range(k):
        step = size + (1 if n < extra else 0)
        out.append(items[i:i + step])
        i += step
    return out


def _member(it):
    return {k: it.get(k) for k in ("repo", "url", "description", "stars_week", "stars_total", "language")}


def plan_cards(items):
    """Top SINGLE_CARDS repos -> one card each; the rest -> cards of 2-3 repos of the same field. Deterministic; ranks are kept.

    [{entity_id, keyword, mode: single|group, tag, members: [{repo, url, description, stars_week, stars_total, language}]}]"""
    items = sorted(items, key=lambda i: i["rank"])
    cards = [{"entity_id": "gh-" + _slug(i["repo"]), "keyword": i["repo"].split("/")[1], "mode": "single", "tag": i["tag"], "members": [_member(i)]}
             for i in items[:SINGLE_CARDS]]
    by_tag, leftovers = {}, []
    for i in items[SINGLE_CARDS:]:
        by_tag.setdefault(i["tag"], []).append(i)
    for tag in [t for t, v in by_tag.items() if len(v) == 1]:
        leftovers += by_tag.pop(tag)
    if len(leftovers) >= 2:
        by_tag.setdefault("tools", []).extend(leftovers)
        leftovers = []
    groups = [(tag, chunk) for tag, v in by_tag.items() for chunk in _chunks(sorted(v, key=lambda i: i["rank"]))]
    if leftovers:
        if groups:
            smallest = min(range(len(groups)), key=lambda n: len(groups[n][1]))
            groups[smallest] = (groups[smallest][0], sorted(groups[smallest][1] + [leftovers[0]], key=lambda i: i["rank"]))
        else:
            groups = [(leftovers[0]["tag"], leftovers)]
    seen = {}
    for tag, chunk in sorted(groups, key=lambda g: g[1][0]["rank"]):
        seen[tag] = seen.get(tag, 0) + 1
        label = GROUP_LABEL.get(tag, tag)
        cards.append({"entity_id": f"gh-{_slug(tag)}-{seen[tag]}", "keyword": f"{label} {len(chunk)}件(GitHub 急上昇)", "mode": "group", "tag": tag,
                      "members": [_member(i) for i in chunk]})
    return cards


def card_problems(cards):
    out, ids, repos = [], set(), set()
    for c in cards:
        if c["entity_id"] in ids:
            out.append(f"{c['entity_id']}: duplicate id")
        ids.add(c["entity_id"])
        if not 1 <= len(c["members"]) <= GROUP_MAX:
            out.append(f"{c['entity_id']}: 1-{GROUP_MAX} repos per card")
        for m in c["members"]:
            if m["repo"] in repos:
                out.append(f"{m['repo']}: in two cards")
            repos.add(m["repo"])
            if m["url"] != f"https://github.com/{m['repo']}":
                out.append(f"{m['repo']}: bad url")
    return out


TAG_OF_FIELD = {"coding-agent": ["tools", "agents"], "infra": ["tools", "local-llm"], "data": ["tools"], "learning": ["tools"], "media": ["tools"]}


def card_trends(week, covered_urls, first_rank, trend_label="baseline"):
    """Trend entries (data/trends.json shape) for the week's frozen card plan; repos already covered by another trend are left out.
    The digest then researches each card from the repos' READMEs like any other candidate."""
    plan = ROOT / "data" / "reports" / week / "github_cards.json"
    if not plan.exists():
        return []
    cards = []
    for c in json.loads(plan.read_text(encoding="utf-8")):
        members = [m for m in c["members"] if m["url"] not in covered_urls]
        if members:
            cards.append({**c, "members": members})
    top = max((sum(m["stars_week"] for m in c["members"]) for c in cards), default=1) or 1
    out = []
    for n, c in enumerate(cards):
        m0, members = c["members"][0], c["members"]
        total = sum(m["stars_week"] for m in members)
        listing = " / ".join(f"{m['repo']}(+{m['stars_week']:,}★): {(m.get('description') or '')[:60]}" for m in members)
        event = [{"kind": "trending", "source": "github_trending", "url": m["url"], "published_at": None, "source_type": "trending",
                  "title": m["repo"], "vendor": None, "date_basis": "observed", "event_id": None} for m in members]
        out.append({
            "rank": first_rank + n, "keyword": c["keyword"], "entity_id": c["entity_id"], "kind": "repo", "category": "github-trending",
            "tags": TAG_OF_FIELD.get(c["tag"], ["tools"]), "score": round(40 + 45 * total / top, 1), "vendor": None,
            "primary": {"url": m0["url"], "published_at": None, "date_basis": "observed", "source_type": "trending", "title": m0["repo"], "event_id": None},
            "events": event[:5],
            "sources": [{"name": "github_trending", "title": m["repo"], "url": m["url"], "metric": float(m["stars_week"]), "metric_name": "stars_week"} for m in members],
            "official_urls": [m["url"] for m in members][:3], "official_verified": False,
            "summary": f"GitHub 急上昇(週間): {listing}"[:400], "slides": [], "score_breakdown": {"github_trending": float(total)},
            "velocity": {"factor": 1.0}, "why": {"first_seen": None, "peak_day": None, "co_mentioned": [], "evidence": []},
            "related": [], "resolved_repo": None, "trend_label": trend_label, "x_posts": [],
            "members": [{k: m.get(k) for k in ("repo", "url", "description", "stars_week", "stars_total", "language")} for m in members]})
    return out


def api_payload():
    """All committed weekly reports, newest last: {latest_week, weeks: [report...]} for api/v1/github.json and the page."""
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "data" / "reports").glob("*/github_top.json"))]
    return {"latest_week": reports[-1]["week"] if reports else None, "tags": TAGS,
            "note": "GitHub Trending(週間)から AI 関連の repo だけを抜き出し、今週増えたスター数で並べたものです。一言解説は付いている場合のみ表示します。",
            "weeks": reports}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    a = ap.parse_args(argv)
    from analyze.report import make_window
    week = a.week or make_window(datetime.now(timezone.utc))["label"]
    src = RAW / "github_weekly.json"
    if not src.exists():
        print("github_top: no raw data; the previous report file (if any) is kept")
        return 0
    out = ROOT / "data" / "reports" / week / "github_top.json"
    previous = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    report = build(json.loads(src.read_text(encoding="utf-8")), week, previous)
    bad = problems(report)
    if bad:
        print("github_top: invalid report, not written:", *bad, sep="\n  ")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    plan = out.with_name("github_cards.json")
    if not plan.exists():  # frozen for the week: a mid-week refresh must not reshuffle entities that may already be published
        cards = plan_cards(report["items"])
        bad = card_problems(cards)
        if bad:
            print("github_top: invalid card plan:", *bad, sep="\n  ")
            return 1
        plan.write_text(json.dumps(cards, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"github_top: {week} -> {len(report['items'])} repos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
