"""Velocity: how many Hacker News stories mention a term this week vs the previous week (Algolia nbHits).
Used to separate 'always present' topics from genuinely rising ones."""
import urllib.parse as up
from concurrent.futures import ThreadPoolExecutor

from .common import SINCE_TS, get_json

WEEK = 7 * 24 * 3600


def _count(term, lo, hi):
    url = "https://hn.algolia.com/api/v1/search?" + up.urlencode(
        {"query": f'"{term}"', "tags": "story", "numericFilters": f"created_at_i>{lo},created_at_i<={hi},points>5", "hitsPerPage": 1})
    try:
        return get_json(url, timeout=15, retries=1).get("nbHits", 0)
    except Exception:
        return None


def hn_velocity(terms, workers=8):
    """terms: list of strings -> {term: (this_week, prev_week) or None}"""
    def one(t):
        cur, prev = _count(t, SINCE_TS, SINCE_TS + WEEK), _count(t, SINCE_TS - WEEK, SINCE_TS)
        return None if cur is None or prev is None else (cur, prev)
    with ThreadPoolExecutor(workers) as ex:
        return dict(zip(terms, ex.map(one, terms)))
