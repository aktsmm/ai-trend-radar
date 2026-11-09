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
    print(f"github_top: {week} -> {len(report['items'])} repos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
