"""Keyword extraction + cross-source scoring -> data/trends.json"""
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone

from collect import x as xmod
from collect.velocity import hn_velocity
from collect.common import RAW, ROOT, X_URL_RE, NOW, SINCE_DATE
from collect.sources import SOURCES
from .lexicon import L, VENDOR_PATTERNS

WEIGHT = {"hf_models": 1.0, "hf_spaces": 0.5, "hf_papers": 0.8, "github_new": 0.9, "github_trending": 1.0, "hackernews": 1.0,
          "reddit_localllama": 1.0, "reddit_ollama": 0.7, "reddit_ml": 0.6, "lobsters": 0.6, "devto": 0.5, "arxiv": 0.3,
          "ollama": 0.6, "openrouter": 0.6, "pypi": 0.5, "bluesky": 0.5}
RANK_SOURCES = {"reddit_localllama", "reddit_ollama", "reddit_ml", "ollama"}
FLAT_SOURCES = {"arxiv", "openrouter"}
TAGS = ["models", "local-llm", "hardware", "agents", "vendor", "tools", "research"]
TAG_CAP = 4
VENDOR_CAP = 2
TOP_N = 20

NOISE = set("""gguf awq gptq fp8 fp4 fp16 bf16 int4 int8 mlx bnb 4bit 8bit 3bit 6bit nvfp4 mxfp4 instruct chat it base uncensored abliterated
lora quantized quant quants exl2 exl3 onnx safetensors merged merge ft sft dpo preview hf mlc gguf-q4 q4 q5 q6 q8 k m s l xl heretic
unsloth bartowski mradermacher lmstudio community thinking reasoning distill distilled v1 opus""".split())
STOP = set("""the a an and or for with from this that how why what who when new ai llm llms gpt model models open source local agent agents
show hn ask tell using use used build built made make your you our we i it is are be to of in on at by as app api tool tools code
paper claude google openai anthropic meta microsoft nvidia apple amazon github reddit python rust data system systems learning
deep large language small fast free best top first more less all any one two three about into over under after before every
""".split())
SIZE_RE = re.compile(r"^(\d+(\.\d+)?[bmkt]|a\d+(\.\d+)?b|\d+x\d+b|\d{4}|q\d.*|iq\d.*|e\d+b)$", re.I)


def norm(s):
    t = re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
    return " " + re.sub(r"([a-z])\s+(\d)", r"\1\2", t) + " "  # 'qwen 3 8' == 'qwen3 8'


def clean_model_name(raw):
    raw = raw.split("/")[-1].split(":")[0]
    toks = [t for t in re.split(r"[-_ ]+", raw) if t]
    keep = [t for t in toks if t.lower() not in NOISE and not SIZE_RE.match(t)]
    return "-".join(keep)


def vendor_of(name, org=""):
    n = norm(name + " " + org)
    for v, pats in VENDOR_PATTERNS.items():
        for p in pats:
            if f" {p} " in n or any(w.startswith(p) and (len(p) >= 4 or w[len(p):].isdigit()) for w in n.split()):
                return v
    return None


def load():
    items = []
    for name in SOURCES:
        f = RAW / f"{name}.json"
        if f.exists():
            for rank, it in enumerate(json.loads(f.read_text(encoding="utf-8"))):
                it["_i"] = len(items)
                items.append(it)
    status = json.loads((RAW / "_status.json").read_text(encoding="utf-8"))
    return items, status


def strengths(items):
    mx = defaultdict(float)
    cnt = defaultdict(int)
    for it in items:
        mx[it["source"]] = max(mx[it["source"]], it["metric"])
        cnt[it["source"]] += 1
    for it in items:
        s = it["source"]
        if s in RANK_SOURCES:
            it["_s"] = max(0.05, 1 - ((it["rank"] or 1) - 1) / max(cnt[s], 1))
        elif s in FLAT_SOURCES:
            it["_s"] = 0.3
        else:
            it["_s"] = math.log1p(it["metric"]) / math.log1p(mx[s]) if mx[s] > 0 else 0.1
        it["_n"] = norm(it["title"] + " " + (it["text"] or "")[:400])


def discover(items):
    """candidate name -> dict(aliases:set, origin:set, tags:list, own:set(item idx))"""
    C = {}

    def add(name, origin_tags, it=None, alias=None, vendor=None, official=None):
        key = norm(name).strip()
        if len(key) < 3 or key in STOP or key.replace(" ", "").isdigit():
            return
        c = C.setdefault(key, {"name": name, "aliases": {key}, "tags": [], "own": set(), "vendor": vendor, "official": [], "dyn": True})
        for t in origin_tags:
            if t not in c["tags"]:
                c["tags"].append(t)
        if it is not None:
            c["own"].add(it["_i"])
        if vendor and not c["vendor"]:
            c["vendor"] = vendor
        if official and official not in c["official"]:
            c["official"].append(official)
        if alias:
            c["aliases"].add(norm(alias).strip())

    for name, e in L.items():
        key = norm(name).strip()
        C[key] = {"name": name, "aliases": {norm(a).strip() for a in e["aliases"]} | {key}, "tags": list(e["tags"]), "own": set(),
                  "vendor": e["vendor"], "official": [e["url"]] if e["url"] else [], "dyn": False}
    for it in items:
        s, t = it["source"], it["title"]
        if s == "hf_models":
            n = clean_model_name(t)
            tg = ["models"] + (["local-llm"] if any(x in " ".join(it.get("tags", [])).lower() for x in ("gguf",)) else [])
            add(n, tg, it, vendor=vendor_of(n, t.split("/")[0]), official=it["url"])
        elif s == "ollama":
            n = clean_model_name(t)
            add(n, ["local-llm", "models"], it, vendor=vendor_of(n), official=it["url"])
        elif s == "openrouter":
            n = clean_model_name(t)
            add(n, ["models"], it, vendor=vendor_of(n, t.split("/")[0]), official=it["url"])
        elif s in ("github_new", "github_trending"):
            repo = t.split("/")[-1]
            if it["metric"] >= 100 or s == "github_trending":
                d = (it["text"] or "").lower() + " " + " ".join(it.get("topics") or [])
                tg = ["tools"]
                if re.search(r"agent|mcp|skill|claude|codex|copilot", d + repo.lower()):
                    tg = ["agents", "tools"]
                if re.search(r"ollama|llama\.cpp|local|on-device|gguf", d):
                    tg.append("local-llm")
                if re.search(r"gpu|cuda|npu|hardware|fpga", d):
                    tg.append("hardware")
                add(repo, tg, it, official=it["url"])
        elif s == "hf_papers":
            m = re.match(r"^([A-Z][\w\-\.]{2,30}):", t)
            if m:
                add(m.group(1), ["research"], it, official=it["url"])
    # title-regex candidates from text sources (must recur)
    pat = re.compile(r"\b([A-Z][a-z]+\d[\w.\-]*|[A-Z][a-z]+[A-Z]\w+|[A-Z][a-z]{2,}[ -]\d+(?:\.\d+)?(?: [A-Z][a-z]+)?)\b")
    found = defaultdict(set)
    for it in items:
        if it["source"] in ("hackernews", "reddit_localllama", "reddit_ollama", "reddit_ml", "lobsters", "devto", "bluesky"):
            for m in pat.finditer(it["title"]):
                found[m.group(1)].add(it["_i"])
    for name, idxs in found.items():
        if len(idxs) >= 2 and len({items[i]["source"] for i in idxs}) >= 1:
            k = norm(name).strip()
            existed = k in C
            add(name, ["tools"], None, vendor=vendor_of(name))
            if not existed and k in C:
                C[k]["dyn_text"] = True
    # coinages: names seen in GitHub repo names/topics AND mentioned in >=2 discussion items (catches new projects like 'Strata')
    TEXT_SRC = ("hackernews", "reddit_localllama", "reddit_ollama", "reddit_ml", "lobsters", "devto", "bluesky")
    gh_tokens = set()
    for it in items:
        if it["source"] in ("github_new", "github_trending"):
            for part in re.split(r"[/\-_ ]+", it["title"]) + list(it.get("topics") or []):
                for tk in re.findall(r"[A-Z]?[a-z]{5,}|[A-Z]{2,}(?![a-z])", part):
                    gh_tokens.add(tk.lower())
    seen_in = defaultdict(set)
    for it in items:
        if it["source"] in TEXT_SRC:
            for tk in set(re.findall(r"\b[A-Z][a-z]{4,}\b|\b[A-Z][a-z]+[A-Z]\w+\b", it["title"] + " " + (it["text"] or "")[:600])):
                if tk.lower() in gh_tokens:
                    seen_in[tk].add(it["_i"])
    low = defaultdict(int)
    allc = defaultdict(int)
    corpus = " ".join(it["title"] + " " + (it["text"] or "")[:600] for it in items if it["source"] in TEXT_SRC)
    for tk in seen_in:
        n_all = len(re.findall(r"\b%s\b" % re.escape(tk), corpus, re.I))
        low[tk] = len(re.findall(r"\b%s\b" % re.escape(tk.lower()), corpus))
        allc[tk] = max(n_all, 1)
    for tk, idxs in seen_in.items():
        if len(idxs) >= 2 and tk.lower() not in STOP and low[tk] / allc[tk] < 0.6:
            k = norm(tk).strip()
            if k not in C:
                add(tk, ["tools"], None)
                if k in C:
                    C[k]["dyn_text"] = True
                    C[k]["coin"] = True
    return C


def merge_prefix(C):
    """Drop longer dynamic candidates that extend a shorter (>=2 token) dynamic one; e.g. 'qwen image 2 1 turbo uncensored'."""
    keys = sorted((k for k, c in C.items() if c["dyn"]), key=lambda k: len(k.split()))
    dead = set()
    for i, a in enumerate(keys):
        ta = a.split()
        if len(ta) < 2 or a in dead:
            continue
        for b in keys[i + 1:]:
            if b != a and b not in dead and b.split()[:len(ta)] == ta:
                C[a]["own"] |= C[b]["own"]
                C[a]["official"] += [u for u in C[b]["official"] if u not in C[a]["official"]]
                for t in C[b]["tags"]:
                    if t not in C[a]["tags"]:
                        C[a]["tags"].append(t)
                dead.add(b)
    for k in dead:
        del C[k]
    # text-derived fragments contained in a longer candidate (e.g. 'image 2 1' in 'qwen image 2 1') are duplicates
    for k in [k for k, c in C.items() if c.get("dyn_text")]:
        if len(k.split()) >= 2 and re.search(r"\d", k) and any(o != k and f" {k} " in f" {o} " for o in C):
            del C[k]
        elif C[k]["vendor"]:
            C[k]["tags"] = ["models"]


def score(items, C, xposts):
    by_src_idx = defaultdict(list)
    for it in items:
        by_src_idx[it["source"]].append(it)
    results = []
    for key, c in C.items():
        hits = defaultdict(list)
        for it in items:
            if it["_i"] in c["own"] or any(len(a) >= 3 and f" {a} " in it["_n"] for a in c["aliases"]):
                hits[it["source"]].append(it)
        if not hits:
            continue
        breakdown = {}
        total = 0.0
        for s, lst in hits.items():
            ss = sorted((i["_s"] for i in lst), reverse=True)
            v = min(1.5, ss[0] + 0.25 * sum(ss[1:4]))
            breakdown[s] = round(v * WEIGHT[s], 3)
            total += v * WEIGHT[s]
        groups = {SOURCES[s][1] for s in hits}
        n_src = len(hits)
        # dynamic text-only names need independent confirmation; structured names may stand alone if strong
        if c.get("dyn_text") and n_src < 2 and sum(len(v) for v in hits.values()) < 3:
            continue
        if n_src < 2 and total < 0.9 and not (set(hits) & {"official", "gh_releases"}):
            continue
        total += 0.25 * (len(groups) - 1)
        results.append({"key": key, "c": c, "hits": hits, "pre": total, "breakdown": breakdown, "groups": groups})
    return results


def attach_x(results, items, xposts):
    for r in results:
        al = [a for a in r["c"]["aliases"] if len(a) >= 3]
        posts = []
        for p in xposts.values():
            if p.get("failed"):
                continue
            hay = norm(p.get("text", "") + " " + p.get("author", ""))
            if any(f" {a} " in hay for a in al):
                posts.append(p)
        r["x_posts"] = posts
        raw = sum(math.log1p(p["likes"] + 2 * p["reposts"] + p["views"] / 200) for p in posts)
        r["x_score"] = round(min(0.5, 0.5 * raw / math.log1p(50000) / 2), 3) if posts else 0.0


def main():
    items, status = load()
    strengths(items)
    C = discover(items)
    merge_prefix(C)
    results = score(items, C, {})

    # --- X integration ---
    x_meta = {"fxtwitter_links": 0, "brave": "skipped (BRAVE_API_KEY not set)", "brave_queries": 0, "posts_fetched": 0}
    links = xmod.collect_links(items)
    x_meta["fxtwitter_links"] = len(links)
    brave_urls = {}
    import os
    if os.environ.get("BRAVE_API_KEY"):
        x_meta["brave"] = "used"
        for r in sorted(results, key=lambda r: -r["pre"])[:30]:
            try:
                for u in xmod.brave_search(r["c"]["name"]) or []:
                    brave_urls.setdefault(u, []).append(r["key"])
                x_meta["brave_queries"] += 1
            except Exception as e:
                x_meta["brave"] = f"partial/failed: {type(e).__name__}"
                break
    all_urls = list(links) + [u for u in brave_urls if u not in links]
    cache = xmod.enrich(all_urls) if all_urls else {}
    xposts = {}
    for u in all_urls:
        sid = X_URL_RE.search(u).group(2)
        p = cache.get(sid)
        if p and not p.get("failed"):
            p = dict(p)
            p["_cited"] = links.get(u, [])
            p["_via"] = "link" if u in links else "brave"
            xposts[sid] = p
    x_meta["posts_fetched"] = len(xposts)
    attach_x(results, items, xposts)

    results.sort(key=lambda r: -(r["pre"] + r["x_score"]))
    pool = results[:150]
    vel = hn_velocity([r["c"]["name"] for r in pool])
    for r in results:
        r["vel"] = vel.get(r["c"]["name"])
        r["factor"] = rising_factor(r["vel"])
        if r["c"].get("coin") and r["vel"] and sum(r["vel"]) >= 8:
            r["factor"] = 0.0  # coined-looking token but widely used on HN = common word / established name
        r["total"] = r["pre"] * r["factor"] + r["x_score"]
    results.sort(key=lambda r: -r["total"])
    pool = results[:80]
    annotate_why(pool, items)
    themes = make_themes(pool, items)
    mx = results[0]["total"]
    out = []
    for r in results[:120]:
        out.append(build_entry(r, mx, items))
    selected = select(out)
    curated = json.loads((ROOT / "data" / "curated.json").read_text(encoding="utf-8")) if (ROOT / "data" / "curated.json").exists() else {}
    for e in selected:
        cur = curated.get(e["keyword"])
        if cur and e["rank"] <= 3:
            e["official_urls"], e["slides"], e["official_verified"] = cur["official_urls"], cur["slides"], True
    data = {
        "generated_at": NOW.isoformat(), "window": {"from": SINCE_DATE, "to": NOW.strftime("%Y-%m-%d")},
        "source_status": status["sources"], "x_integration": x_meta, "trends": selected, "themes": themes, "candidates_pool": len(results),
    }
    (ROOT / "data" / "trends.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "site" / "data.js").write_text("window.TRENDS = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    for e in selected:
        print(f"{e['rank']:>2} {e['score']:5.1f} {e['keyword']:<34} {','.join(e['tags']):<26} {e.get('vendor') or '-':<10} src={len(e['sources'])} x={e['score_breakdown'].get('x_aux', 0)}")


def rising_factor(vel):
    """Down-weight evergreen topics: ratio of HN stories this week vs previous week (4x or more = full weight)."""
    if not vel or sum(vel) < 3:
        return 0.7
    g = math.log2((vel[0] + 1) / (vel[1] + 1))
    return max(0.35, min(1.0, 0.35 + 0.65 * g / 2))


def annotate_why(pool, items):
    """Why is it rising? first-seen date, co-mentioned keywords (likely trigger / context), strongest evidence items."""
    sets = [{i["_i"] for l in r["hits"].values() for i in l} for r in pool]
    for n, r in enumerate(pool):
        co = []
        for m, r2 in enumerate(pool):
            if m == n or r2["key"] in r["key"] or r["key"] in r2["key"]:
                continue
            shared = len(sets[n] & sets[m])
            if shared >= 2:
                co.append((shared, r2["c"]["name"]))
        co.sort(reverse=True)
        dated = sorted(i["created"][:10] for l in r["hits"].values() for i in l if i.get("created"))
        peak = max(set(dated), key=dated.count) if dated else None
        top_items = sorted((i for l in r["hits"].values() for i in l if i["source"] in ("reddit_localllama", "hackernews", "lobsters", "reddit_ollama", "github_new", "hf_papers")),
                           key=lambda i: -i["_s"])[:3]
        r["why"] = {"first_seen": dated[0] if dated else None, "peak_day": peak,
                    "co_mentioned": [c for _, c in co[:5]],
                    "evidence": [{"source": i["source"], "title": i["title"][:140], "url": i["url"]} for i in top_items]}


def make_themes(pool, items, min_shared=3):
    """Cluster keywords that share discussion items -> 'what is going on' themes."""
    parent = list(range(len(pool)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    sets = [{i["_i"] for l in r["hits"].values() for i in l if i["source"] not in ("arxiv", "pypi")} for r in pool]
    for a in range(len(pool)):
        for b in range(a + 1, len(pool)):
            inter = len(sets[a] & sets[b])
            if inter >= min_shared and inter / max(1, min(len(sets[a]), len(sets[b]))) >= 0.35:
                parent[find(a)] = find(b)
    groups = defaultdict(list)
    for n in range(len(pool)):
        groups[find(n)].append(n)
    themes = []
    for g in groups.values():
        if len(g) < 3:
            continue
        cnt = defaultdict(int)
        for n in g:
            for i in sets[n]:
                cnt[i] += 1
        shared = sorted(cnt, key=lambda i: -cnt[i])[:4]
        themes.append({"keywords": [pool[n]["c"]["name"] for n in sorted(g, key=lambda n: -pool[n]["total"])][:10],
                       "evidence": [{"source": items[i]["source"], "title": items[i]["title"][:140], "url": items[i]["url"]} for i in shared]})
    themes.sort(key=lambda t: -len(t["keywords"]))
    return themes[:6]


def build_entry(r, mx, items):
    c = r["c"]
    srcs = []
    for s, lst in r["hits"].items():
        for it in sorted(lst, key=lambda i: -i["_s"])[:2]:
            srcs.append({"name": s, "title": it["title"][:120], "url": it["url"], "metric": it["metric"], "metric_name": it["metric_name"]})
    tags = [t for t in c["tags"] if t in TAGS]
    # evidence-based tags
    hs = set(r["hits"])
    if hs & {"reddit_localllama", "reddit_ollama", "ollama"} and "local-llm" not in tags and len(tags) < 2:
        tags.append("local-llm")
    if "hf_papers" in hs and "research" not in tags and not c["dyn"]:
        tags.append("research")
    blob = norm(c["name"] + " " + " ".join(i["title"] for l in r["hits"].values() for i in l[:2]))
    if re.search(r" (gpu|rtx|npu|vram|nvidia|amd|tpu|cuda|apple silicon|m\d max|chip|hardware) ", blob) and "hardware" not in tags and len(tags) < 3:
        tags.append("hardware")
    tags = tags[:3] or ["tools"]
    best = max((i for l in r["hits"].values() for i in l), key=lambda i: i["_s"] * WEIGHT[i["source"]])
    bd = dict(r["breakdown"])
    if r["x_score"]:
        bd["x_aux"] = r["x_score"]
    nsrc = len(r["hits"])
    official = [u for u in c["official"] if u][:3]
    desc = next((i["text"] for l in r["hits"].values() for i in l if i["source"] in ("ollama", "github_new", "github_trending", "hf_papers") and i["text"]), "")
    return {
        "keyword": c["name"], "tags": tags, "score": round(100 * r["total"] / mx, 1), "vendor": c["vendor"],
        "sources": srcs, "official_urls": official, "official_verified": not c["dyn"],
        "summary": f"{nsrc}個のソース({', '.join(sorted(r['hits']))})で言及。代表: 「{best['title'][:80]}」" + (f" / {desc[:100]}" if desc else ""),
        "slides": [], "score_breakdown": bd,
        "velocity": {"hn_this_week": r["vel"][0], "hn_prev_week": r["vel"][1], "factor": round(r["factor"], 2)} if r["vel"] else {"factor": round(r["factor"], 2)},
        "why": r.get("why", {}),
        "x_posts": [{"url": p["url"], "author": p["author"], "likes": p["likes"], "reposts": p["reposts"], "views": p["views"],
                     "text": p["text"][:200], "via": p["_via"]} for p in sorted(r["x_posts"], key=lambda p: -p["likes"])[:3]],
    }


def select(cands):
    sel, per_tag, per_vendor = [], defaultdict(int), defaultdict(int)
    for e in cands:
        if len(sel) >= TOP_N:
            break
        p = e["tags"][0]
        if per_tag[p] >= TAG_CAP or (e["vendor"] and per_vendor[e["vendor"]] >= VENDOR_CAP):
            continue
        per_tag[p] += 1
        if e["vendor"]:
            per_vendor[e["vendor"]] += 1
        e["rank"] = len(sel) + 1
        sel.append(e)
    return sel


if __name__ == "__main__":
    main()
