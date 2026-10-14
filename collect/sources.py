"""Per-source collectors. Each returns a list of normalized items (see common.item)."""
import os
import re
import threading
import time
import urllib.parse as up
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .common import (SINCE_DATE, SINCE_TS, extract_x_urls, get, get_json, item, strip_html)

AI_RE = re.compile(r"\b(ai|llm|llms|gpt|agent|agents|model|models|ollama|llama|claude|gemini|mcp|rag|diffusion|transformer|inference|gpu|local)\b", re.I)


def hf_models():
    d = get_json("https://huggingface.co/api/models?sort=trendingScore&limit=60")
    return [item("hf_models", m["id"], f"https://huggingface.co/{m['id']}", m.get("pipeline_tag", ""),
                 m.get("trendingScore", 0), "trendingScore", i + 1, m.get("createdAt"),
                 likes=m.get("likes"), downloads=m.get("downloads"), tags=m.get("tags", [])[:15])
            for i, m in enumerate(d)]


def hf_spaces():
    d = get_json("https://huggingface.co/api/spaces?sort=trendingScore&limit=30")
    return [item("hf_spaces", s["id"], f"https://huggingface.co/spaces/{s['id']}", "",
                 s.get("trendingScore", 0), "trendingScore", i + 1, s.get("createdAt"), likes=s.get("likes"))
            for i, s in enumerate(d)]


def hf_papers():
    d = get_json("https://huggingface.co/api/daily_papers?limit=40")
    out = []
    for i, e in enumerate(d):
        p = e.get("paper", {})
        out.append(item("hf_papers", p.get("title") or e.get("title"), f"https://huggingface.co/papers/{p.get('id')}",
                        p.get("summary", ""), p.get("upvotes", 0), "upvotes", i + 1, p.get("publishedAt"),
                        github=p.get("githubRepo"), org=(p.get("organization") or {}).get("name")))
    return out


def github_search():
    queries = ["llm", "ai agent", "ollama OR llama.cpp OR \"local llm\"", "mcp server", "rag OR \"vector database\"",
               "inference gpu llm", "claude OR gpt OR gemini"]
    hdr = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        hdr["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    seen, out = set(), []
    for q in queries:
        url = "https://api.github.com/search/repositories?" + up.urlencode(
            {"q": f"{q} created:>{SINCE_DATE}", "sort": "stars", "order": "desc", "per_page": 20})
        try:
            r = get_json(url, hdr)
        except Exception:
            continue
        for repo in r.get("items", []):
            if repo["full_name"] in seen:
                continue
            seen.add(repo["full_name"])
            out.append(item("github_new", repo["full_name"], repo["html_url"], repo.get("description") or "",
                            repo["stargazers_count"], "stars", None, repo["created_at"],
                            topics=repo.get("topics", []), homepage=repo.get("homepage"), language=repo.get("language")))
    if not out:
        raise RuntimeError("github search returned nothing (rate limit?)")
    out.sort(key=lambda x: -x["metric"])
    return out


def github_trending():
    html = get("https://github.com/trending?since=weekly")
    out = []
    for i, art in enumerate(html.split("<article")[1:]):
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', art)
        if not m:
            continue
        repo = m.group(1).strip()
        desc = re.search(r"<p[^>]*>(.*?)</p>", art, re.S)
        st = re.search(r"([\d,]+)\s+stars this week", art)
        out.append(item("github_trending", repo, f"https://github.com/{repo}", strip_html(desc.group(1)) if desc else "",
                        int(st.group(1).replace(",", "")) if st else 0, "stars_week", i + 1))
    if not out:
        raise RuntimeError("no trending parsed")
    return out


def hackernews():
    qs = ["LLM", "local LLM", "ollama", "AI agent", "Claude", "GPT", "Gemini", "llama.cpp", "MCP", "Qwen", "DeepSeek",
          "NVIDIA GPU AI", "open weights", "Codex", "Cursor AI"]
    seen, out = {}, []
    for q in qs:
        url = "https://hn.algolia.com/api/v1/search?" + up.urlencode(
            {"query": q, "tags": "story", "numericFilters": f"created_at_i>{SINCE_TS},points>25", "hitsPerPage": 40})
        try:
            r = get_json(url)
        except Exception:
            continue
        for h in r.get("hits", []):
            if h["objectID"] in seen:
                continue
            seen[h["objectID"]] = 1
            out.append(item("hackernews", h.get("title"), h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
                            strip_html(h.get("story_text") or ""), h.get("points", 0), "points", None, h.get("created_at"),
                            comments=h.get("num_comments"), hn_id=h["objectID"]))
    if not out:
        raise RuntimeError("no HN hits")
    out.sort(key=lambda x: -x["metric"])
    return out


_reddit_lock = threading.Lock()


def _atom(url, source):
    with _reddit_lock:  # serialize: Reddit rate-limits parallel RSS requests
        time.sleep(2)
        root = ET.fromstring(get(url, retries=3))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for i, e in enumerate(root.findall("a:entry", ns)):
        title = e.findtext("a:title", "", ns)
        link = e.find("a:link", ns)
        content = e.findtext("a:content", "", ns)
        urls = re.findall(r'href="([^"]+)"', content)
        out.append(item(source, title, link.get("href") if link is not None else "", strip_html(content), 0, "rank", i + 1,
                        e.findtext("a:updated", "", ns), links=[u for u in urls if "reddit.com" not in u][:5],
                        raw_html=content[:4000]))
    return out


def reddit_localllama():
    return _atom("https://www.reddit.com/r/LocalLLaMA/top/.rss?t=week&limit=100", "reddit_localllama")


def reddit_ollama():
    return _atom("https://www.reddit.com/r/ollama/top/.rss?t=week&limit=50", "reddit_ollama")


def reddit_machinelearning():
    return _atom("https://www.reddit.com/r/MachineLearning/top/.rss?t=week&limit=50", "reddit_ml")


def lobsters():
    out = []
    for page in (1, 2):
        for s in get_json(f"https://lobste.rs/t/ai.json?page={page}"):
            if s["created_at"][:10] >= SINCE_DATE:
                out.append(item("lobsters", s["title"], s.get("url") or s["comments_url"], s.get("description_plain", ""),
                                s["score"], "score", None, s["created_at"], comments=s.get("comment_count"),
                                comments_url=s["comments_url"], tags=s.get("tags")))
    if not out:
        raise RuntimeError("no lobsters stories")
    return out


def devto():
    seen, out = set(), []
    for tag in ("llm", "ai", "agents", "ollama", "mcp"):
        try:
            r = get_json(f"https://dev.to/api/articles?tag={tag}&top=7&per_page=30")
        except Exception:
            continue
        for a in r:
            if a["id"] in seen:
                continue
            seen.add(a["id"])
            out.append(item("devto", a["title"], a["url"], a.get("description", ""), a.get("public_reactions_count", 0),
                            "reactions", None, a.get("published_at"), tags=a.get("tag_list")))
    if not out:
        raise RuntimeError("no dev.to")
    out.sort(key=lambda x: -x["metric"])
    return out


def arxiv():
    q = up.quote("cat:cs.CL OR cat:cs.AI OR cat:cs.LG")
    root = ET.fromstring(get(f"http://export.arxiv.org/api/query?search_query={q}&sortBy=submittedDate&sortOrder=descending&max_results=80",
                             timeout=40))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    return [item("arxiv", strip_html(e.findtext("a:title", "", ns)), e.findtext("a:id", "", ns),
                 strip_html(e.findtext("a:summary", "", ns)), 1, "paper", None, e.findtext("a:published", "", ns))
            for e in root.findall("a:entry", ns)]


def ollama_library():
    html = get("https://ollama.com/library?sort=newest")
    out, seen = [], set()
    for blk in re.split(r"<li\s", html)[1:]:
        m = re.search(r'href="/library/([^"]+)"', blk)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        desc = re.search(r"<p[^>]*text-md[^>]*>(.*?)</p>", blk, re.S)
        out.append(item("ollama", m.group(1), f"https://ollama.com/library/{m.group(1)}", strip_html(desc.group(1)) if desc else "",
                        0, "rank", len(out) + 1, None, info=strip_html(blk)[-120:]))
    if not out:
        raise RuntimeError("no ollama models parsed")
    return out[:60]


def openrouter():
    d = get_json("https://openrouter.ai/api/v1/models")["data"]
    out = [item("openrouter", m["id"], f"https://openrouter.ai/{m['id']}", m.get("name", ""), 1, "new_model", None,
                datetime.fromtimestamp(m["created"], timezone.utc).isoformat())
           for m in d if m.get("created", 0) >= SINCE_TS]
    return out


PYPI_PKGS = ["vllm", "llama-cpp-python", "ollama", "transformers", "langchain", "langgraph", "mcp", "openai-agents",
             "crewai", "pydantic-ai", "mlx-lm", "unsloth", "sglang"]


def pypi_stats():
    out = []
    for p in PYPI_PKGS:
        try:
            r = get_json(f"https://pypistats.org/api/packages/{p}/recent")["data"]
        except Exception:
            continue
        out.append(item("pypi", p, f"https://pypi.org/project/{p}/", "", r.get("last_week", 0), "downloads_week"))
    if not out:
        raise RuntimeError("pypistats failed")
    return out


def bluesky():
    out, seen = [], set()
    for q in ("LLM", "ollama", "local llm", "AI agent", "Claude", "Qwen", "llama.cpp"):
        url = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?" + up.urlencode(
            {"q": q, "sort": "top", "since": SINCE_DATE + "T00:00:00Z", "limit": 25})
        try:
            r = get_json(url)
        except Exception:
            continue
        for p in r.get("posts", []):
            if p["uri"] in seen:
                continue
            seen.add(p["uri"])
            rec = p.get("record", {})
            likes = p.get("likeCount", 0) + 2 * p.get("repostCount", 0)
            out.append(item("bluesky", (rec.get("text") or "")[:140], "https://bsky.app/profile/%s/post/%s" % (p["author"]["handle"], p["uri"].split("/")[-1]),
                            rec.get("text", ""), likes, "likes+2*reposts", None, rec.get("createdAt")))
    if not out:
        raise RuntimeError("bluesky returned nothing")
    return out


# name -> (function, domain group used for balance reporting)
SOURCES = {
    "hf_models": (hf_models, "models"), "hf_spaces": (hf_spaces, "models"), "hf_papers": (hf_papers, "research"),
    "github_new": (github_search, "tools"), "github_trending": (github_trending, "tools"),
    "hackernews": (hackernews, "community"), "reddit_localllama": (reddit_localllama, "local-llm"),
    "reddit_ollama": (reddit_ollama, "local-llm"), "reddit_ml": (reddit_machinelearning, "research"),
    "lobsters": (lobsters, "community"), "devto": (devto, "community"), "arxiv": (arxiv, "research"),
    "ollama": (ollama_library, "local-llm"), "openrouter": (openrouter, "vendor"), "pypi": (pypi_stats, "tools"),
    "bluesky": (bluesky, "community"),
    "official": (None, "vendor"), "gh_releases": (None, "tools"),  # filled by collect.run.run_official
}
