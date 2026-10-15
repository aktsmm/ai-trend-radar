"""Japanese-language reactions (display only, NOT used for ranking): Zenn / Qiita / Hatena Bookmark public RSS feeds.

Yahoo! Realtime Search has no official API and its terms do not allow scraping, so it is intentionally not collected.
Items are matched to published keywords by title in analyze.report.attach_jp and shown as links with a '日本語の反応' label.
"""
from datetime import timedelta

from .common import SINCE, get, item
from .official import parse_feed

FEEDS = [
    ("zenn", "https://zenn.dev/topics/llm/feed"),
    ("zenn", "https://zenn.dev/topics/ai/feed"),
    ("qiita", "https://qiita.com/tags/llm/feed"),
    ("qiita", "https://qiita.com/tags/ai/feed"),
    ("hatena", "https://b.hatena.ne.jp/search/tag?q=LLM&mode=rss"),
    ("hatena", "https://b.hatena.ne.jp/search/tag?q=AI&mode=rss"),
]


def collect_jp():
    """Returns (items, status). Each failing feed is recorded but never fails the run."""
    out, seen, stat = [], set(), {}
    for site, url in FEEDS:
        try:
            n = 0
            for title, link, pub, summ in parse_feed(get(url, timeout=25, retries=1)):
                if pub and pub >= SINCE and link and link not in seen and title:
                    seen.add(link)
                    out.append(item("jp_reaction", title, link, summ, 0, "", None, pub.isoformat(), site=site))
                    n += 1
            stat[url] = {"ok": True, "count": n}
        except Exception as e:
            stat[url] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:120]}
    return out, stat
