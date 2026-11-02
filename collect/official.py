"""Official announcement sources (allowlist). Each feed is an independent collector; failures are recorded, never fatal.

Item fields: source='official'|'gh_releases', vendor, source_type, feed, published (ISO), url, title.
"""
import html
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
    # qwenlm.github.io stopped updating in 2025-09 and qwen.ai/blog is JS-rendered; Qwen releases are caught through the HF org (collect.sources.HF_ORGS).
    ("anthropic-news", "Anthropic", "announcement", "https://www.anthropic.com/news"),
    ("mistral-news", "Mistral", "announcement", "https://mistral.ai/news/rss"),
    # ai.meta.com/blog/rss/ was removed (404/400); the Meta newsroom feed is used instead, filtered to AI topics (AI_ONLY_FEEDS).
    ("meta-newsroom", "Meta", "announcement", "https://about.fb.com/news/feed/"),
    ("google-research-blog", "Google", "announcement", "https://research.google/blog/rss/"),
    ("microsoft-research-blog", "Microsoft", "announcement", "https://www.microsoft.com/en-us/research/feed/"),
    ("apple-ml-research", "Apple", "announcement", "https://machinelearning.apple.com/rss.xml"),
    ("nvidia-genai-blog", "NVIDIA", "announcement", "https://blogs.nvidia.com/blog/category/generative-ai/feed/"),
    # deepseek.com is intentionally not collected (only the official GitHub releases are).
    ("ollama-blog", "Ollama", "announcement", "https://ollama.com/blog/rss.xml"),
]
AI_ONLY_FEEDS = {"meta-newsroom"}
# Vendors without an RSS feed: the blog index page is scraped for article links, and each new article's own page gives the date
# (og / article:published_time / JSON-LD). Keeps launches like Liquid AI's LFM3 from depending on third-party mentions.
# (blog_id, vendor, index_url, link_regex)
BLOG_INDEXES = [
    ("liquid-blog", "Liquid AI", "https://www.liquid.ai/blog", r'href="(/blog/[a-z0-9][^"#?/]*)"'),
    ("kimi-blog", "Moonshot AI", "https://www.kimi.com/blog", r'href="(/blog/[a-z0-9][^"#?/]*)"'),
    ("minimax-news", "MiniMax", "https://www.minimax.io/news", r'href="(/news/[a-z0-9][^"#?/]*)"'),
    ("allenai-blog", "Ai2", "https://allenai.org/blog", r'href="(/blog/[a-z0-9][^"#?/]*)"'),
    ("cohere-blog", "Cohere", "https://cohere.com/blog", r'href="(/blog/[a-z0-9][^"#?/]*)"'),
    ("together-blog", "Together AI", "https://www.together.ai/blog", r'href="(/blog/[a-z0-9][^"#?/]*)"'),
]
PAGE_DATE_RES = [re.compile(p, re.I) for p in (
    r'property=["\']article:published_time["\']\s+content=["\']([^"\']+)', r'content=["\']([^"\']+)["\']\s+property=["\']article:published_time',
    r'"datePublished"\s*:\s*"([^"]+)"', r'<time[^>]+datetime=["\']([^"\']+)', r'name=["\']date["\']\s+content=["\']([^"\']+)',
    r'"dateModified"\s*:\s*"([^"]+)"',  # last resort: some sites only expose the modified date, which is never earlier than the announcement
    r'>((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, 20\d\d)<',  # a visible "Month D, YYYY" byline
)]
TITLE_RE = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)|<title>([^<]+)</title>', re.I)
AI_RE = re.compile(r"\b(ai|llama|llm|model|models|agent|agents|superintelligence|glasses|smart glasses|gpu|inference)\b", re.I)
# official GitHub repositories -> Releases atom
GH_REPOS = [
    ("ggml-org/llama.cpp", "ggml"), ("ollama/ollama", "Ollama"), ("vllm-project/vllm", "vLLM"), ("sgl-project/sglang", "SGLang"),
    ("anthropics/claude-code", "Anthropic"), ("openai/codex", "OpenAI"), ("google-gemini/gemini-cli", "Google"),
    ("huggingface/transformers", "HuggingFace"),  # Qwen / DeepSeek publish on HF (HF_ORGS), their GitHub repos have no releases
    ("ml-explore/mlx", "Apple"), ("unslothai/unsloth", "Unsloth"), ("open-webui/open-webui", "OpenWebUI"),
    ("modelcontextprotocol/servers", "Anthropic"), ("microsoft/agent-framework", "Microsoft"), ("github/copilot-cli", "Microsoft"),
    ("openai/openai-agents-python", "OpenAI"), ("langchain-ai/langgraph", "LangChain"),
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
            for fmt in ("%B %d, %Y", "%b %d, %Y"):  # "October 27, 2026" / "Oct 27, 2026"
                try:
                    d = datetime.strptime(s, fmt)
                    break
                except Exception:
                    continue
            else:
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
    """HTML list page (no RSS), three layouts seen so far:
    card: <time> then the card's /news/<slug> link with <h3>/<img alt> title;
    row:  /news/<slug> link, then <time>, then a '<title> details' region (the link precedes the date);
    old:  href + 'Mon D, YYYY' + category + title."""
    categories = {"announcements", "product", "policy", "research", "features", "societal-impacts", "interpretability",
                  "alignment", "customer-stories", "economic-research", "engineering", "education", "safety"}
    out, seen = [], set()
    times = list(re.finditer(r"<time[^>]*>\s*([A-Z][a-z]{2} \d{1,2}, \d{4})\s*</time>", html_text))

    def slugs(text):
        # a category link's text is a single capitalised word ("Partnerships"); real posts have a title
        def is_post(m):
            label = re.match(r"[^>]*>\s*([^<]*)<", text[m.end():m.end() + 200])
            return m.group(1).rsplit("/", 1)[1] not in categories and not (label and re.fullmatch(r"[A-Z][A-Za-z ]{2,24}", label.group(1).strip()) and len(label.group(1).split()) <= 2)
        return [m for m in re.finditer(r'href="(/news/[^"#?/]+)"', text) if is_post(m)]

    def clean(raw):
        return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))).strip()[:160]

    for i, t in enumerate(times):
        end = times[i + 1].start() if i + 1 < len(times) else len(html_text)
        after = html_text[t.end():min(end, t.end() + 3000)]
        details = re.match(r'.{0,300}?aria-label="([^"]+?) details"', after, re.S)
        first_link = slugs(after)[:1]
        if details and (not first_link or details.start(1) < first_link[0].start()):
            before = html_text[max(0, t.start() - 3000):t.start()]
            prior = max((m.end() for m in re.finditer(r"<time[^>]*>[^<]*</time>", before)), default=0)
            back = slugs(before[prior:])
            if not back:
                continue
            slug, title = back[-1].group(1), clean(details.group(1))
        elif first_link:
            slug = first_link[0].group(1)
            h3 = re.search(r"<h3[^>]*>(.*?)</h3>", after, re.S)
            alt = re.search(r'<img[^>]*\balt="([^"]+)"', after)
            title = clean(h3.group(1) if h3 else alt.group(1) if alt else "")
        else:
            continue
        if not title or slug in seen:
            continue
        seen.add(slug)
        out.append((title, "https://www.anthropic.com" + slug, _dt(datetime.strptime(t.group(1), "%b %d, %Y").isoformat()), ""))
    if out:
        return out
    cats = r"(?:Announcements|Policy|Product|Research|Societal impacts|Interpretability|Alignment|Customer stories|Economic Research|Engineering|Education|Safety)"
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


def fetch_blog(blog):
    """Scrape a blog index for article links (newest first); read each article page for its title and publication date. Only dated, in-window articles count."""
    import html as _html
    import urllib.parse as up
    bid, vendor, index, rx = blog
    page = get(index, timeout=30, retries=1)
    links, out = [], []
    for m in re.finditer(rx, page):
        u = up.urljoin(index, m.group(1))
        if u not in links and u.rstrip("/") != index.rstrip("/"):
            links.append(u)
    for u in links[:6]:  # the index lists newest first; older ones were collected on earlier days
        try:
            art = get(u, timeout=25, retries=1)
        except Exception:
            continue
        pub = next((_dt(m.group(1)) for rx_ in PAGE_DATE_RES for m in [rx_.search(art)] if m and _dt(m.group(1))), None)
        t = TITLE_RE.search(art)
        title = strip_html(_html.unescape((t.group(1) or t.group(2)) if t else "")).split(" | ")[0].strip()
        if pub and pub >= SINCE and title:
            out.append(item("official", title, u, "", 1, "announcement", None, pub.isoformat(), vendor=vendor, source_type="announcement", feed=bid))
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
        fid = arg[0]
        url = arg[3] if kind == "feed" else arg[2] if kind == "blog" else f"https://github.com/{arg[0]}/releases.atom"
        try:
            res = fetch_feed(arg) if kind == "feed" else fetch_blog(arg) if kind == "blog" else fetch_release(arg)
            return fid, res, {"ok": True, "count": len(res), "url": url}
        except Exception as e:
            return fid, [], {"ok": False, "error": f"{type(e).__name__}: {e}"[:200], "url": url}

    jobs = [("feed", f) for f in FEEDS] + [("blog", b) for b in BLOG_INDEXES] + [("rel", r) for r in GH_REPOS]
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
