"""Official announcement sources (allowlist). Each feed is an independent collector; failures are recorded, never fatal.

Item fields: source='official'|'gh_releases', vendor, source_type, feed, published (ISO), url, title.
"""
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .common import NOW, SINCE, get, item, strip_html

# (feed_id, vendor, source_type, url)
FEEDS = [
    ("openai-news", "OpenAI", "announcement", "https://openai.com/news/rss.xml"),
    ("google-ai-blog", "Google", "announcement", "https://blog.google/technology/ai/rss/"),
    ("deepmind-blog", "Google", "announcement", "https://deepmind.google/blog/rss.xml"),
    ("nvidia-blog", "NVIDIA", "announcement", "https://blogs.nvidia.com/feed/"),
    ("nvidia-dev-blog", "NVIDIA", "announcement", "https://developer.nvidia.com/blog/feed/"),
    ("aws-ml-blog", "AWS", "announcement", "https://aws.amazon.com/blogs/machine-learning/feed/"),
    ("aws-whats-new", "AWS", "release_note", "https://aws.amazon.com/about-aws/whats-new/recent/feed/"),
    ("microsoft-foundry-blog", "Microsoft", "announcement", "https://devblogs.microsoft.com/foundry/feed/"),
    ("github-changelog", "Microsoft", "release_note", "https://github.blog/changelog/feed/"),
    ("huggingface-blog", "HuggingFace", "announcement", "https://huggingface.co/blog/feed.xml"),
    ("qwen-blog", "Alibaba", "announcement", "https://qwenlm.github.io/blog/index.xml"),
    ("anthropic-news", "Anthropic", "announcement", "https://www.anthropic.com/news"),
    ("mistral-news", "Mistral", "announcement", "https://mistral.ai/news/rss"),
    # ai.meta.com/blog/rss/ was removed (404/400); the Meta newsroom feed is used instead, filtered to AI topics (AI_ONLY_FEEDS).
    ("meta-newsroom", "Meta", "announcement", "https://about.fb.com/news/feed/"),
    ("google-research-blog", "Google", "announcement", "https://research.google/blog/rss/"),
    ("microsoft-research-blog", "Microsoft", "announcement", "https://www.microsoft.com/en-us/research/feed/"),
    ("apple-ml-research", "Apple", "announcement", "https://machinelearning.apple.com/rss.xml"),
    ("nvidia-genai-blog", "NVIDIA", "announcement", "https://blogs.nvidia.com/blog/category/generative-ai/feed/"),
    # deepseek.com is blocked by the corporate IT policy (Windows Security notice, 2026-10-15): intentionally not collected.
    ("ollama-blog", "Ollama", "announcement", "https://ollama.com/blog/rss.xml"),
]
AI_ONLY_FEEDS = {"meta-newsroom"}
AI_RE = re.compile(r"\b(ai|llama|llm|model|models|agent|agents|superintelligence|glasses|smart glasses|gpu|inference)\b", re.I)
# official GitHub repositories -> Releases atom
GH_REPOS = [
    ("ggml-org/llama.cpp", "ggml"), ("ollama/ollama", "Ollama"), ("vllm-project/vllm", "vLLM"), ("sgl-project/sglang", "SGLang"),
    ("anthropics/claude-code", "Anthropic"), ("openai/codex", "OpenAI"), ("google-gemini/gemini-cli", "Google"),
    ("QwenLM/Qwen3", "Alibaba"), ("deepseek-ai/DeepSeek-V3", "DeepSeek"), ("huggingface/transformers", "HuggingFace"),
    ("ml-explore/mlx", "Apple"), ("unslothai/unsloth", "Unsloth"), ("open-webui/open-webui", "OpenWebUI"),
    ("modelcontextprotocol/servers", "Anthropic"), ("microsoft/autogen", "Microsoft"), ("github/copilot-cli", "Microsoft"),
]


def _dt(s):
    from datetime import datetime
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def parse_feed(xml_text):
    """RSS 2.0 / RDF / Atom -> [(title, link, published_dt, summary)]"""
    xml_text = re.sub(r"^\ufeff", "", xml_text.strip())
    root = ET.fromstring(xml_text)
    out = []
    for e in root.iter():
        tag = e.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        g = {c.tag.split("}")[-1]: c for c in e}
        title = strip_html((g["title"].text if "title" in g else "") or "")
        link = ""
        if "link" in g:
            link = g["link"].get("href") or (g["link"].text or "")
        pub = next((g[k].text for k in ("pubDate", "published", "date", "updated") if k in g and g[k].text), None)
        summ = strip_html((g["description"].text if "description" in g else g["summary"].text if "summary" in g else "") or "")[:400]
        out.append((title, link.strip(), _dt(pub), summ))
    return out


def parse_anthropic_news(html_text):
    """HTML list page (no RSS): href + 'Mon D, YYYY' + category + title."""
    cats = r"(?:Announcements|Policy|Product|Research|Societal impacts|Interpretability|Alignment|Customer stories|Economic Research|Engineering|Education|Safety)"
    out, seen = [], set()
    for m in re.finditer(r'href="(/news/[^"#?]+)"', html_text):
        slug = m.group(1)
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_text[m.end():m.end() + 500])).strip()
        d = re.match(r"(?:[\w\-=\"/ ]*>\s*)?([A-Z][a-z]{2} \d{1,2}, \d{4})\s+(?:%s\s+)?(.+)" % cats, txt)
        if slug in seen or not d:
            continue
        seen.add(slug)
        title = re.split(r"\s+(?:Oct|Sep|Aug|Jul|Jun|May|Apr|Mar|Feb|Jan|Nov|Dec) \d{1,2}, \d{4}", d.group(2))[0][:160]
        out.append((title, "https://www.anthropic.com" + slug, _dt(datetime.strptime(d.group(1), "%b %d, %Y").isoformat()), ""))
    return out


def fetch_feed(feed):
    fid, vendor, stype, url = feed
    out = []
    text = get(url, timeout=30, retries=1)
    entries = parse_anthropic_news(text) if fid == "anthropic-news" else parse_feed(text)
    for title, link, pub, summ in entries:
        if pub and pub >= SINCE and title and link:
            out.append(item("official", title, link, summ, 1, "announcement", None, pub.isoformat(),
                            vendor=vendor, source_type=stype, feed=fid))
    return out


def fetch_release(repo_vendor):
    repo, vendor = repo_vendor
    out = []
    for title, link, pub, summ in parse_feed(get(f"https://github.com/{repo}/releases.atom", timeout=30, retries=1)):
        if pub and pub >= SINCE:
            out.append(item("gh_releases", f"{repo.split('/')[1]} {title}", link, summ, 1, "release", None, pub.isoformat(),
                            vendor=vendor, source_type="release_note", feed=repo, repo=repo))
    return out


def collect_official():
    """Returns (items, ledger) ; ledger[feed_id] = {ok, count, error, url}"""
    items, ledger = [], {}

    def run(job):
        kind, arg = job
        fid = arg[0] if kind == "feed" else arg[0]
        url = arg[3] if kind == "feed" else f"https://github.com/{arg[0]}/releases.atom"
        try:
            res = fetch_feed(arg) if kind == "feed" else fetch_release(arg)
            return fid, res, {"ok": True, "count": len(res), "url": url}
        except Exception as e:
            return fid, [], {"ok": False, "error": f"{type(e).__name__}: {e}"[:200], "url": url}

    jobs = [("feed", f) for f in FEEDS] + [("rel", r) for r in GH_REPOS]
    with ThreadPoolExecutor(6) as ex:
        for fid, res, led in ex.map(run, jobs):
            items += res
            ledger[fid] = led
    return items, ledger


def collect_all():
    """-> (official_items, release_items, ledger). Raises only if every feed failed."""
    items, ledger = collect_official()
    if not any(l["ok"] for l in ledger.values()):
        raise RuntimeError("all official feeds failed")
    return ([i for i in items if i["source"] == "official"], [i for i in items if i["source"] == "gh_releases"], ledger)
