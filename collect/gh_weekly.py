"""AI-filtered weekly GitHub trending ("今週の GitHub 急上昇 AI repo").

github.com/trending?since=weekly is read for the overall list and a few languages (AI repos are easier to find per language),
merged, reduced to AI-related repos (GitHub topics + description/name keywords) with a minimum total-star floor, and ranked by
stars gained this week. Output goes to data/raw/github_weekly.json (not committed); analyze.github_top turns it into the report file.
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor

from .common import get, get_json, save_raw, strip_html

LANGS = ["", "python", "typescript", "rust", "go"]
MIN_TOTAL_STARS = 500
KEEP = 30
AI_TOPICS = {"llm", "llms", "ai", "artificial-intelligence", "machine-learning", "deep-learning", "agent", "ai-agents", "agents",
             "mcp", "model-context-protocol", "rag", "generative-ai", "chatgpt", "claude", "claude-code", "openai", "anthropic",
             "ollama", "llama", "inference", "embeddings", "prompt-engineering", "copilot", "transformers", "diffusion", "nlp"}
AI_TERMS = re.compile(r"\b(llms?|ai|agents?|agentic|mcp|rag|claude|gpt|gemini|openai|anthropic|ollama|llama|inference|embeddings?|"
                      r"prompts?|copilot|cursor|transformers?|diffusion|ontology|machine learning|deep learning|neural|chatbot|generative)\b", re.I)
PROMO_RE = re.compile(r"airdrop|casino|nsfw|uncensored|jailbreak|crack(ed)?\b|referral|giveaway", re.I)


def parse_trending(html):
    """-> [{repo, description, stars_week, stars_total, language}] in page order."""
    out = []
    for art in html.split("<article")[1:]:
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"?#]+)"', art)
        if not m:
            continue
        desc = re.search(r'<p[^>]*class="[^"]*\bmy-1\b[^"]*"[^>]*>(.*?)</p>', art, re.S)  # other <p> tags hold button labels ("Sponsor", "Star")
        week = re.search(r"([\d,]+)\s+stars this week", art)
        total = re.search(r'href="/[^"]+/stargazers"[^>]*>(.*?)</a>', art, re.S)
        lang = re.search(r'itemprop="programmingLanguage"[^>]*>\s*([^<]+?)\s*<', art)
        digits = re.sub(r"[^\d]", "", strip_html(total.group(1))) if total else ""
        out.append({"repo": re.sub(r"\s+", "", m.group(1)), "description": strip_html(desc.group(1)) if desc else "",
                    "stars_week": int(week.group(1).replace(",", "")) if week else 0,
                    "stars_total": int(digits) if digits else None, "language": lang.group(1) if lang else None})
    return out


def exclusion(entry, topics):
    """None when the repo is an AI repo worth listing, otherwise the reason it is left out."""
    text = f"{entry['repo']} {entry['description']}"
    if PROMO_RE.search(text):
        return "promo / unsafe wording"
    if not (set(topics) & AI_TOPICS or AI_TERMS.search(text.replace("-", " ").replace("_", " "))):
        return "not AI related"
    if entry["stars_total"] is not None and entry["stars_total"] < MIN_TOTAL_STARS:
        return f"under {MIN_TOTAL_STARS} total stars"
    return None


def _topics(repo):
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    try:
        d = get_json(f"https://api.github.com/repos/{repo}", headers, timeout=15, retries=1)
        return [t.lower() for t in d.get("topics", [])], d.get("html_url"), d.get("pushed_at")
    except Exception:
        return [], None, None


def merge(pages):
    best = {}
    for entries in pages:
        for e in entries:
            if e["repo"] not in best or e["stars_week"] > best[e["repo"]]["stars_week"]:
                best[e["repo"]] = e
    return sorted(best.values(), key=lambda e: -e["stars_week"])


def build(pages, topics_of):
    items, excluded = [], []
    for e in merge(pages):
        topics, _, pushed = topics_of(e["repo"])
        why = exclusion(e, topics)
        if why:
            excluded.append({"repo": e["repo"], "reason": why})
            continue
        items.append({**e, "url": f"https://github.com/{e['repo']}", "topics": topics[:8], "pushed_at": pushed})
    return {"items": items[:KEEP], "excluded": excluded}


def github_weekly():
    def page(lang):
        try:
            return parse_trending(get("https://github.com/trending" + (f"/{lang}" if lang else "") + "?since=weekly"))
        except Exception:
            return None

    with ThreadPoolExecutor(5) as ex:
        pages = list(ex.map(page, LANGS))
    ok = [p for p in pages if p]
    if not ok:
        raise RuntimeError("no trending page could be parsed")
    repos = [e["repo"] for e in merge(ok)][:60]
    with ThreadPoolExecutor(8) as ex:
        cache = dict(zip(repos, ex.map(_topics, repos)))
    result = build(ok, lambda r: cache.get(r, ([], None, None)))
    result.update(pages_ok=len(ok), pages_total=len(LANGS))
    if not result["items"]:
        raise RuntimeError("trending parsed but no AI repo passed the filter")
    return result


def collect():
    result = github_weekly()
    save_raw("github_weekly", result)
    return result
