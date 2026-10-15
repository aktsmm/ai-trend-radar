"""Weekly report v2: event-centred TOP (products / models / releases / papers / hardware) with primary-source gate.

python -m analyze.report [--week 2026-W42] [--offline]
Writes data/reports/<YYYY-Www>/report.json (+ data/trends.json, site/data.js as 'latest').
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import yaml
from urllib import parse as up
from collect import x as xmod
from collect.common import RAW, ROOT, X_URL_RE, get_json
from collect.velocity import hn_velocity
from . import build as B

B.WEIGHT.update({"official": 0.8, "gh_releases": 0.6})
JST = timezone(timedelta(hours=9))
UTC = timezone.utc
SLOTS = {"model": 5, "dev-tool": 4, "local-runtime": 4, "hardware": 2, "research": 3, "github-trending": 2}
COMMUNITY = {"hackernews", "reddit_localllama", "reddit_ollama", "reddit_ml", "lobsters", "devto", "bluesky"}
CAT_TAG = {"model": "models", "dev-tool": "agents", "local-runtime": "local-llm", "hardware": "hardware", "research": "research",
           "github-trending": "tools"}
PRIORITY = {"official": 0, "gh_releases": 1, "hf_papers": 2, "hf_models": 2, "github_new": 3, "openrouter": 4, "github_trending": 5}
SOURCE_TYPE = {"gh_releases": "release_note", "hf_models": "model_card", "hf_papers": "paper", "github_new": "repo",
               "openrouter": "catalog", "github_trending": "trending"}
OFFICIAL_TYPES = {"announcement", "release_note", "docs", "product_page"}
OFFICIAL_DOMAINS = ("openai.com", "anthropic.com", "claude.com", "blog.google", "deepmind.google", "nvidia.com", "aws.amazon.com",
                    "microsoft.com", "devblogs.microsoft.com", "huggingface.co", "qwenlm.github.io", "mistral.ai", "ollama.com",
                    "github.blog", "github.com")
PROMO_RE = re.compile(r"airdrop|casino|free money|crack(ed)?|nsfw|uncensored|jailbreak|referral|100x|pump|giveaway", re.I)
ENT_RE = re.compile(r"\b([A-Z][A-Za-z]*[0-9][\w.\-]*(?: [A-Z][a-z]+)?|[A-Z][a-z]+[A-Z]\w+|[A-Z][a-z]{2,} \d+(?:\.\d+)?(?: [A-Z][a-z]+)?)\b")


# ---------- time window ----------
def parse_dt(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)


def make_window(now, week=None):
    """[start, end) in UTC. A named week is Monday 00:00 JST to next Monday 00:00 JST; default is rolling 7 days (partial)."""
    if week:
        y, w = week.split("-W")
        mon = datetime.fromisocalendar(int(y), int(w), 1).replace(tzinfo=JST)
        start, end = mon.astimezone(UTC), (mon + timedelta(days=7)).astimezone(UTC)
        return {"start": start, "end": end, "label": week, "partial": end > now}
    iso = now.astimezone(JST).isocalendar()
    return {"start": now - timedelta(days=7), "end": now, "label": f"{iso[0]}-W{iso[1]:02d}", "partial": True}


# ---------- candidates ----------
def load_stoplist():
    d = yaml.safe_load((ROOT / "data" / "stoplist.yml").read_text(encoding="utf-8"))
    return {B.norm(x).strip() for k in d for x in d[k]}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def add_official_candidates(C, items):
    all_aliases = [a for c in C.values() for a in c["aliases"] if len(a) >= 3]
    for it in items:
        if it["source"] != "official":
            continue
        n = B.norm(it["title"])
        if any(f" {a} " in n for a in all_aliases):
            continue
        m = ENT_RE.search(it["title"])
        if not m:
            continue
        key = B.norm(m.group(1)).strip()
        if len(key) < 4 or key in B.STOP or key in C:
            continue
        C[key] = {"name": m.group(1), "aliases": {key}, "tags": ["tools"], "own": {it["_i"]}, "vendor": B.vendor_of(m.group(1)) or it.get("vendor"),
                  "official": [it["url"]], "dyn": True}


def make_events(c, hits, items, win):
    evs, outside = [], 0
    for s, lst in hits.items():
        if s not in PRIORITY:
            continue
        for it in lst:
            if s != "gh_releases" and it["_i"] not in c["own"] and not any(f" {a} " in B.norm(it["title"]) for a in c["aliases"] if len(a) >= 3):
                continue  # entity must be the subject (title), not an incidental mention in the body
            if s == "github_trending":
                evs.append(dict(kind="trending", source=s, url=it["url"], published_at=None, source_type="trending",
                                title=it["title"], vendor=None, date_basis="observed"))
                continue
            if s in ("hf_models", "github_new", "openrouter") and c["vendor"] and "/" in it["title"]:
                org = it["title"].split("/")[0]
                if B.vendor_of("", org) != c["vendor"] and B.norm(org).strip() not in (B.norm(c["vendor"]).strip(), *c["aliases"]):
                    continue  # community re-uploads / third-party repos are not the vendor's primary source
            dt = parse_dt(it.get("created"))
            if not dt or not (win["start"] <= dt < win["end"]):
                outside += 1
                continue
            if s == "gh_releases" and B.norm(it["repo"].split("/")[1]).strip() not in c["aliases"]:
                continue  # a release note of another project that merely mentions the entity is not its primary source
            st = it.get("source_type") if s == "official" else SOURCE_TYPE[s]
            evs.append(dict(kind={"gh_releases": "release", "hf_papers": "paper", "hf_models": "model", "openrouter": "model",
                                  "github_new": "repo"}.get(s, "announcement"),
                            source=s, url=it["url"], published_at=dt.isoformat(), source_type=st, title=it["title"][:140],
                            vendor=it.get("vendor"), date_basis="published", feed=it.get("feed")))
    for e in evs:
        e["event_id"] = hashlib.sha1((slug(c["name"]) + e["url"]).encode()).hexdigest()[:10]
    def key(e):
        mismatch = 1 if e["vendor"] and c["vendor"] and e["vendor"] != c["vendor"] else 0
        return (mismatch, PRIORITY[e["source"]], -(parse_dt(e["published_at"]).timestamp() if e["published_at"] else 0), e["url"])
    evs.sort(key=key)
    return evs, outside


def desc_of(c, hits):
    """Description from an item whose title is about the entity (not an incidental mention in someone else's text)."""
    for s in ("official", "gh_releases", "ollama", "hf_papers", "github_new", "github_trending"):
        for it in hits.get(s, []):
            if it["text"] and (it["_i"] in c["own"] or any(f" {a} " in B.norm(it["title"]) for a in c["aliases"] if len(a) >= 3)):
                return it["text"]
    return ""


RESEARCH_FEEDS = {"google-research-blog", "microsoft-research-blog", "apple-ml-research", "deepmind-blog"}


def categorize(c, hits, desc, events):
    names = set(hits)
    blob = B.norm(c["name"] + " " + desc)
    t0 = (c["tags"] or [""])[0]
    if (events and (events[0]["source"] == "hf_papers" or events[0].get("feed") in RESEARCH_FEEDS)) or names == {"hf_papers"} or (t0 == "research" and not c["vendor"]):
        return "research"
    if t0 == "hardware" or re.search(r" (gpu|npu|fpga|accelerator|chip|tpu|jetson|dgx|rtx) ", B.norm(c["name"])):
        return "hardware"
    runtime_re = re.search(r" (inference engine|llm runtime|llama cpp|gguf|moe inference|local llm|on device) ", blob)
    if runtime_re or (not c["dyn"] and t0 == "local-llm"):
        return "local-runtime"
    if t0 == "models" or names & {"hf_models", "openrouter", "ollama"}:
        return "model"
    gh_only = names <= {"github_new", "github_trending"} | {"reddit_localllama", "reddit_ollama", "hackernews", "lobsters", "devto", "bluesky"} and names & {"github_new", "github_trending"}
    if gh_only and not (c["tags"] and c["tags"][0] in ("agents",)):
        if not re.search(r" (agent|mcp|cli|coding|copilot|claude|codex|sdk) ", blob):
            return "github-trending"
    return "dev-tool"


def resolve_gh_repo(c, hits, api):
    """Find 'owner/Name' mentions whose repo part equals the candidate alias; returns repo json or None."""
    pat = re.compile(r"github\.com/([\w.\-]+)/([\w.\-]+)|\b([\w.\-]{2,})/([A-Za-z][\w.\-]{2,})\b")
    seen = set()
    for lst in hits.values():
        for it in lst:
            for m in pat.finditer((it.get("raw_html") or "") + " " + (it.get("text") or "") + " " + " ".join(it.get("links") or [])):
                o, r = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
                if f" {B.norm(r).strip()} " in {f" {a} " for a in c["aliases"]} and (o, r) not in seen:
                    seen.add((o, r))
                    j = api(f"{o}/{r}")
                    if j:
                        return j
    if c["dyn"] and len(c["name"].split()) == 1 and len(c["name"]) >= 5:
        return api("search:" + c["name"])
    return None


def repo_events(j, win, name):
    """Primary-source events for a resolved GitHub project: an official release inside the window, else creation inside it."""
    from collect.official import parse_feed
    from collect.common import get
    full = j["full_name"]
    evs = []
    try:
        for title, link, pub, _ in parse_feed(get(f"https://github.com/{full}/releases.atom", timeout=20, retries=0)):
            if pub and win["start"] <= pub < win["end"]:
                evs.append(dict(kind="release", source="gh_releases", url=link, published_at=pub.isoformat(), source_type="release_note",
                                title=f"{full} {title}"[:140], vendor=None, date_basis="published"))
    except Exception:
        pass
    dt = parse_dt(j.get("created_at"))
    if dt and win["start"] <= dt < win["end"]:
        evs.append(dict(kind="repo", source="github_new", url=j["html_url"], published_at=dt.isoformat(), source_type="repo",
                        title=full, vendor=None, date_basis="published"))
    for e in evs:
        e["event_id"] = hashlib.sha1((slug(name) + e["url"]).encode()).hexdigest()[:10]
    evs.sort(key=lambda e: (PRIORITY[e["source"]], -parse_dt(e["published_at"]).timestamp()))
    return evs


def gh_api_factory(offline):
    cache = {}
    hdr = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token and not offline:
        try:  # local convenience: reuse the gh CLI login (never printed or stored)
            import subprocess
            token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10).stdout.strip() or None
        except Exception:
            token = None
    if token:
        hdr["Authorization"] = "Bearer " + token

    def api(full):
        if offline:
            return None
        if full not in cache:
            try:
                if full.startswith("search:"):  # best exact-name repo match, accepted only if it looks like an AI project
                    q = full[7:]
                    res = get_json("https://api.github.com/search/repositories?" + up.urlencode(
                        {"q": f"{q} in:name", "sort": "stars", "per_page": 5}), hdr, timeout=15, retries=0)
                    cache[full] = next((x for x in res.get("items", []) if B.norm(x["name"]).strip() == B.norm(q).strip()
                                        and x["stargazers_count"] >= 100
                                        and re.search(r"llm|inference|model|\bai\b|agent|gpu|neural", (x.get("description") or "").lower())), None)
                else:
                    cache[full] = get_json(f"https://api.github.com/repos/{full}", hdr, timeout=15, retries=0)
            except Exception:
                cache[full] = None
        return cache[full]
    return api


def gh_quality(c, hits, api, repo_counts):
    """Explainable rules, applied only to a narrowed candidate set. Returns (ok, reasons)."""
    reasons = []
    for s in ("github_new", "github_trending"):
        for it in hits.get(s, [])[:1]:
            full = it["title"]
            j = api(full)
            if j:
                if j.get("fork"):
                    reasons.append("fork")
                if j.get("archived"):
                    reasons.append("archived")
                if not (j.get("description") or "").strip():
                    reasons.append("empty description")
                if PROMO_RE.search((j.get("description") or "") + " " + full):
                    reasons.append("promotional wording")
            owner = full.split("/")[0]
            if it["source"] == "github_trending" and it["metric"] >= 50000:
                reasons.append(f"anomalous weekly stars ({int(it['metric'])})")
            if repo_counts.get(owner, 0) >= 3:
                reasons.append(f"same-author mass repos ({repo_counts[owner]})")
    return (not reasons), reasons


# ---------- report ----------
def build_report(items, status, now, week=None, xposts=None, vel=None, stoplist=None, offline=False, snapshots_n=0, ledger=None,
                 watch_posts=None, brave_urls=None):
    win = make_window(now, week)
    stoplist = load_stoplist() if stoplist is None else stoplist
    B.strengths(items)
    C = B.discover(items)
    add_official_candidates(C, items)
    B.merge_prefix(C)
    lex_aliases = {a for c in C.values() if not c["dyn"] for a in c["aliases"]}
    for k in [k for k, c in C.items() if c["dyn"] and k in lex_aliases]:
        del C[k]  # e.g. dynamic 'Codex' duplicates lexicon 'OpenAI Codex'
    results = B.score(items, C, {})
    dropped_stop = [r["c"]["name"] for r in results if r["key"] in stoplist or r["c"]["name"] and B.norm(r["c"]["name"]).strip() in stoplist]
    results = [r for r in results if r["key"] not in stoplist and B.norm(r["c"]["name"]).strip() not in stoplist]

    api = gh_api_factory(offline)
    for r in results:
        r["desc"] = desc_of(r["c"], r["hits"])
        r["events"], r["outside"] = make_events(r["c"], r["hits"], items, win)
    # resolve the project's own GitHub repo (owner/Name mentions) for strong dynamic candidates without an official primary event
    need = sorted((r for r in results if r["c"]["dyn"] and not any(e["source"] in ("official", "gh_releases") and e["published_at"] for e in r["events"])),
                  key=lambda r: (-bool(r["c"].get("coin")), -r["pre"]))[:40]
    for r in need:
        j = resolve_gh_repo(r["c"], r["hits"], api)
        if j:
            r["resolved_repo"] = {"url": j["html_url"], "created_at": j.get("created_at"), "stars": j.get("stargazers_count"),
                                  "description": j.get("description")}
            r["events"] = repo_events(j, win, r["c"]["name"]) + r["events"]
            r["desc"] = r["desc"] or (j.get("description") or "")
    pending, gated = [], []
    for r in results:
        r["category"] = categorize(r["c"], r["hits"], r["desc"], r["events"])
        if r["category"] == "hardware":  # model cards / repos that merely carry the name are not hardware announcements
            r["events"] = [e for e in r["events"] if e["source"] in ("official", "gh_releases")]
        has_pub = any(e["published_at"] for e in r["events"])
        trending_ok = r["category"] == "github-trending" and any(e["kind"] == "trending" for e in r["events"])
        r["primary"] = r["events"][0] if r["events"] and (has_pub or trending_ok) else None
        (gated if r["primary"] else pending).append(r)

    # buzz across community sources (+X), then velocity on the narrowed pool
    attach = xposts or {}
    B.attach_x(gated, items, attach)
    gated.sort(key=lambda r: (-(r["pre"] + r["x_score"]), r["key"]))
    pool = gated[:120]
    vel = vel if vel is not None else ({} if offline else hn_velocity([r["c"]["name"] for r in pool]))

    def suspect(c):  # coined-looking / single TitleCase word: real new names are rare on HN, common words are not
        return c["dyn"] and (c.get("coin") or c.get("dyn_text") or (len(c["name"].split()) == 1 and c["name"].isalpha() and c["name"][1:].islower()))
    gated = [r for r in gated if not (suspect(r["c"]) and vel.get(r["c"]["name"]) and sum(vel[r["c"]["name"]]) >= 8)]
    for r in gated:
        r["vel"] = vel.get(r["c"]["name"])
        f = B.rising_factor(r["vel"])
        if r["primary"]["source"] in ("official", "gh_releases"):
            f = max(f, 0.6)  # an official release/announcement this week is itself the 'new' signal
        r["factor"] = f
        bonus = {"official": 0.6, "gh_releases": 0.35}.get(r["primary"]["source"], 0.15)
        n_comm = sum(len(v) for s, v in r["hits"].items() if s in COMMUNITY)
        bonus += 0.35 * math.log2(1 + n_comm) / 2  # discussion volume (distinct posts), not just the best post
        bonus += 0.08 * min(6, sum(1 for e in r["events"] if e["source"] == "gh_releases"))  # release cadence
        r["total"] = r["pre"] * f + bonus + r["x_score"]
    gated.sort(key=lambda r: (-r["total"], r["key"]))

    # GitHub quality rules on the narrowed set (API, optional)
    owners = defaultdict(int)
    for it in items:
        if it["source"] in ("github_new", "github_trending") and "/" in it["title"]:
            owners[it["title"].split("/")[0]] += 1
    kept, rejected = [], []
    for n, r in enumerate(gated):
        if n < 40 and (set(r["hits"]) & {"github_new", "github_trending"}) and not (set(r["hits"]) & {"official", "gh_releases", "hf_models", "hf_papers"}):
            ok, why = gh_quality(r["c"], r["hits"], api, owners)
            if not ok:
                rejected.append({"keyword": r["c"]["name"], "reasons": why})
                continue
        kept.append(r)
    gated = kept
    mx = gated[0]["total"] if gated else 1

    # merge same-vendor candidates within a category into the strongest, best-evidenced one
    reps, merged = {}, []
    for r in gated:
        v = r["c"]["vendor"]
        k = (v, r["category"]) if v else ("", r["key"])
        if k in reps:
            reps[k]["related"].append(r["c"]["name"])
            merged.append(r["c"]["name"])
        else:
            r["related"] = []
            reps[k] = r
    cands = [r for r in gated if r in reps.values()]

    selected, used = [], set()
    for cat, n in SLOTS.items():
        for r in [r for r in cands if r["category"] == cat][:n]:
            selected.append(r)
            used.add(r["key"])
    for r in cands:
        if len(selected) >= B.TOP_N:
            break
        if r["key"] not in used:
            selected.append(r)
            used.add(r["key"])
    selected.sort(key=lambda r: (-r["total"], r["key"]))
    selected = selected[:B.TOP_N]

    B.annotate_why(selected, items)
    trends = [entry(r, n + 1, mx, snapshots_n) for n, r in enumerate(selected)]
    apply_enrichment(trends, win["label"])
    leads = x_leads(watch_posts or [], selected)
    return {
        "generated_at": now.isoformat(), "last_successful_report_at": now.isoformat(),
        "window": {"from": win["start"].astimezone(JST).strftime("%Y-%m-%d"), "to": win["end"].astimezone(JST).strftime("%Y-%m-%d"),
                   "label": win["label"], "partial": win["partial"], "tz": "JST, [start, end)"},
        "baseline": {"snapshots": snapshots_n, "is_baseline": snapshots_n < 14,
                     "note": "日次スナップショットが14日分たまるまでは『新着/注目』表示で、『上昇中』とは呼ばない"},
        "source_status": status["sources"], "official_ledger": ledger or {},
        "x_integration": {"search": status["sources"].get("x_search"), "watchlist": status["sources"].get("x_watch"),
                          "posts_used": len(attach)},
        "trends": trends,
        "pending": [{"keyword": r["c"]["name"], "reason": "no primary source dated inside the window"} for r in sorted(pending, key=lambda r: -r["pre"])[:25]],
        "rejected": rejected, "merged_vendor_duplicates": merged, "stoplisted": sorted(set(dropped_stop)),
        "leads_unverified": leads,
        "candidates_pool": len(results),
    }


def _topic_tokens(t):
    toks = {B.norm(t["keyword"]), B.norm(t["entity_id"].replace("-", " "))} | {f" {w} " for w in B.norm(t["keyword"]).split() if len(w) >= 5}
    return toks | {B.norm(x) for x in t.get("related", [])}


def attach_jp(trends, jp_items, limit=3):
    """Japanese-language reactions (Zenn/Qiita/Hatena): display-only links whose title names the keyword. Never used for ranking."""
    for t in trends:
        if "keyword" not in t:
            continue
        toks = _topic_tokens(t)
        hits = [x for x in jp_items if any(k.strip() and k in B.norm(x["title"]) for k in toks)]
        t["jp_reactions"] = [{"site": x.get("site", ""), "title": x["title"][:80], "url": x["url"], "date": (x.get("created") or "")[:10]}
                             for x in sorted(hits, key=lambda x: x.get("created") or "", reverse=True)[:limit]]


def on_topic_filter(t):
    """Display-only denoising: keep sources / X posts whose own title or text names the keyword (not just a body-text mention)."""
    if "keyword" not in t:
        return
    toks = _topic_tokens(t)
    hit = lambda s: any(k.strip() and k in B.norm(s) for k in toks)
    on = [s for s in t["sources"] if hit(s["title"]) or s["name"] in ("gh_releases", "official")]
    t["sources"] = on or t["sources"][:1]
    t["x_posts"] = [p for p in t["x_posts"] if hit(p["text"])]


def apply_enrichment(trends, label):
    """Merge Phase-2 MCP verification records and slide JSON (both committed under data/reports/<week>/). Others stay 'unverified'."""
    d = ROOT / "data" / "reports" / label
    enr = json.loads((d / "enrichment.json").read_text(encoding="utf-8")) if (d / "enrichment.json").exists() else {"entities": {}}
    slides = json.loads((d / "slides.json").read_text(encoding="utf-8")) if (d / "slides.json").exists() else {}
    digests = json.loads((d / "digest.json").read_text(encoding="utf-8")) if (d / "digest.json").exists() else {}
    decks = json.loads((d / "decks.json").read_text(encoding="utf-8")) if (d / "decks.json").exists() else {}
    checks = enr.get("url_checks", {})
    for t in trends:
        on_topic_filter(t)
        e = enr["entities"].get(t["entity_id"])
        t["verification"] = {"status": "unverified", "checks": []}
        if not e:
            continue
        t["verification"] = {"status": e["verification_status"], "checks": e["checks"], "selection_reason": e.get("selection_reason")}
        t["official_urls"] = e["official_urls"]
        t["official_verified"] = e["verification_status"] in ("verified", "partially_verified")
        t["url_checks"] = {u: checks.get(u) for u in e["official_urls"]}
        t["slides"] = slides.get(t["entity_id"], [])
        if t["entity_id"] in digests:
            t["digest"] = digests[t["entity_id"]]
        if t["entity_id"] in decks:
            t["deck"] = decks[t["entity_id"]]


def entry(r, rank, mx, snaps):
    c, p = r["c"], r["primary"]
    cat = r["category"]
    kind = {"research": "paper", "hardware": "hardware", "github-trending": "repo"}.get(cat) or (
        "release" if p["source"] == "gh_releases" else "model" if cat == "model" else "product")
    tags = [CAT_TAG[cat]] + [t for t in c["tags"] if t in B.TAGS and t != CAT_TAG[cat] and t != "vendor"]
    srcs = []
    for s, lst in r["hits"].items():
        for it in sorted(lst, key=lambda i: -i["_s"])[:2]:
            srcs.append({"name": s, "title": it["title"][:120], "url": it["url"], "metric": it["metric"], "metric_name": it["metric_name"]})
    official = [u for u in dict.fromkeys(([p["url"]] if p["source_type"] in OFFICIAL_TYPES else []) + [u for u in c["official"] if u]
                                         + ([r["resolved_repo"]["url"]] if r.get("resolved_repo") else []))][:3]
    verified = p["source_type"] in OFFICIAL_TYPES
    best = max((i for l in r["hits"].values() for i in l), key=lambda i: i["_s"] * B.WEIGHT[i["source"]])
    bd = {k: v for k, v in r["breakdown"].items()}
    if r["x_score"]:
        bd["x_aux"] = r["x_score"]
    return {
        "rank": rank, "keyword": c["name"], "entity_id": slug(c["name"]), "kind": kind, "category": cat, "tags": tags[:3],
        "score": round(100 * r["total"] / mx, 1), "vendor": c["vendor"],
        "primary": {"url": p["url"], "published_at": p["published_at"], "date_basis": p["date_basis"], "source_type": p["source_type"],
                    "title": p["title"], "event_id": p["event_id"] if "event_id" in p else None},
        "events": [dict(e) for e in r["events"][:5]],
        "sources": srcs, "official_urls": official, "official_verified": verified,
        "summary": (f"{p['title'][:90]}" + (f" ― {r['desc'][:110]}" if r["desc"] else "") +
                    f"。{len(r['hits'])}ソースで言及(代表: 「{best['title'][:60]}」)"),
        "slides": [], "score_breakdown": bd,
        "velocity": ({"hn_this_week": r["vel"][0], "hn_prev_week": r["vel"][1], "factor": round(r["factor"], 2)} if r.get("vel")
                     else {"factor": round(r["factor"], 2)}),
        "why": r.get("why", {}), "related": r.get("related", []), "resolved_repo": r.get("resolved_repo"),
        "trend_label": "baseline" if snaps < 14 else "rising",
        "x_posts": [{"url": q["url"], "author": q["author"], "likes": q["likes"], "reposts": q["reposts"], "views": q["views"],
                     "text": q["text"][:200], "via": q["_via"]} for q in sorted(r["x_posts"], key=lambda q: -q["likes"])[:3]],
    }


def x_leads(posts, selected):
    """Watchlist posts that link to official-looking pages but are not (yet) tied to a selected, corroborated candidate."""
    chosen = " ".join(" ".join(r["c"]["aliases"]) for r in selected)
    out = []
    for p in sorted(posts, key=lambda p: -p["likes"]):
        text = B.norm(p["text"])
        if any(f" {a} " in text for r in selected for a in r["c"]["aliases"] if len(a) >= 4):
            continue
        links = [u for u in p["links"] if any(urlparse(u).netloc.endswith(d) for d in OFFICIAL_DOMAINS)]
        if links:
            out.append({"author": p["author"], "url": p["url"], "text": p["text"][:160], "links": links[:2], "likes": p["likes"],
                        "status": "unverified: needs official site / release note / GitHub Release corroboration"})
    return out[:15]


def collect_x(items, offline):
    xposts = {}
    if offline:
        return xposts
    links = xmod.collect_links(items)
    cache = xmod.enrich(list(links)) if links else {}
    for u in links:
        sid = X_URL_RE.search(u).group(2)
        p = cache.get(sid)
        if p and not p.get("failed"):
            xposts[sid] = dict(p, _cited=links[u], _via="link")
    return xposts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    now = datetime.now(UTC)
    items, status = B.load()
    watch = json.loads((RAW / "x_watch.json").read_text(encoding="utf-8")) if (RAW / "x_watch.json").exists() else []
    ledger = json.loads((RAW / "_official_ledger.json").read_text(encoding="utf-8")) if (RAW / "_official_ledger.json").exists() else {}
    snaps = len(list((ROOT / "data" / "snapshots").glob("*.json"))) if (ROOT / "data" / "snapshots").exists() else 0
    xposts = collect_x(items, a.offline)
    for p in watch:  # watchlist posts are also scored as auxiliary X evidence
        xposts.setdefault(p["id"], dict(p, _cited=[], _via="watchlist"))
    rep = build_report(items, status, now, a.week, xposts, None, None, a.offline, snaps, ledger, watch)
    jp_path = RAW / "jp_reaction.json"
    if jp_path.exists():
        attach_jp(rep["trends"], json.loads(jp_path.read_text(encoding="utf-8")))
    out = ROOT / "data" / "reports" / rep["window"]["label"]
    out.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(rep, ensure_ascii=False, indent=1)
    (out / "report.json").write_text(txt, encoding="utf-8")
    (ROOT / "data" / "trends.json").write_text(txt, encoding="utf-8")
    (ROOT / "site" / "data.js").write_text("window.TRENDS = " + json.dumps(rep, ensure_ascii=False) + ";\n", encoding="utf-8")
    for t in rep["trends"]:
        print(f"{t['rank']:>2} {t['score']:5.1f} {t['category']:<15} {t['kind']:<9} {t['keyword']:<30} {t['primary']['source_type']:<13} {t['primary']['published_at'] or t['primary']['date_basis']}")
    print("pending:", len(rep["pending"]), "rejected:", len(rep["rejected"]), "leads:", len(rep["leads_unverified"]))


if __name__ == "__main__":
    main()
