"""Deterministic page prefetch for the digest agent: fetch each pending candidate's first-party page(s) OUTSIDE the agent sandbox.

python -m analyze.prefetch            # reads .work/pending.json, writes .work/pages/<entity_id>.json

Why: the agent runs behind a firewall with no usable fetch tool, and page text is untrusted data anyway. This step fetches the candidate's primary
URL plus a few same-host blog/release/docs links, strips markup, extracts a publication-date hint and returns plain text. The agent may only
cite URLs listed in these files (status 200) and dates found here.
"""
import html
import json
import re
import sys
import urllib.parse as up
from datetime import datetime, timezone

from collect.common import ROOT, get

MAX_TEXT = 9000
HOP_RE = re.compile(r"(blog|news|release|changelog|docs|announce|introducing|launch|whats-new|model|about)", re.I)
DATE_RES = [re.compile(p, re.I) for p in (
    r'property=["\']article:published_time["\']\s+content=["\']([^"\']+)',
    r'content=["\']([^"\']+)["\']\s+property=["\']article:published_time',
    r'"datePublished"\s*:\s*"([^"]+)"',
    r'<time[^>]+datetime=["\']([^"\']+)',
    r'name=["\']date["\']\s+content=["\']([^"\']+)',
)]


def text_of(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))).strip()


def get_safe(url):
    try:
        return get(url, timeout=25, retries=1)
    except Exception:
        return ""


def hf_card_url(url):
    """huggingface.co/<org>/<model> pages are dominated by a JSON config blob; the model card text lives in the raw README."""
    m = re.match(r"^https://huggingface\.co/([^/]+/[^/#?]+)/?$", url)
    return f"https://huggingface.co/{m.group(1)}/raw/main/README.md" if m and m.group(1).split("/")[0] not in ("spaces", "datasets", "papers") else None


def fetch(url):
    rec = {"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(), "status": None}
    try:
        raw = get(url, timeout=25, retries=1)
        rec["status"] = 200
    except Exception as e:  # recorded, never fatal
        rec["error"] = f"{type(e).__name__}: {e}"[:160]
        return rec, ""
    for rx in DATE_RES:
        m = rx.search(raw)
        if m:
            rec["published_hint"] = m.group(1)[:40]
            break
    card = hf_card_url(url)
    if card:
        try:
            readme = get(card, timeout=25, retries=1)
            rec["text"] = re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>|!\[[^\]]*\]\([^)]*\)", " ", re.sub(r"(?s)^---.*?---", " ", readme)))).strip()[:MAX_TEXT]  # front matter, HTML and images dropped
            return rec, raw
        except Exception:
            pass
    rec["text"] = text_of(raw)[:MAX_TEXT]
    return rec, raw


def hops(base, raw, limit=3):
    host = up.urlparse(base).netloc
    out, seen = [], {base}
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', raw, re.I | re.S):
        u = up.urljoin(base, html.unescape(m.group(1)))
        if up.urlparse(u).netloc == host and u not in seen and u.startswith("http") and HOP_RE.search(u + " " + text_of(m.group(2))[:80]):
            seen.add(u)
            out.append(u)
        if len(out) >= limit:
            break
    return out


def main():
    pend = json.loads((ROOT / ".work" / "pending.json").read_text(encoding="utf-8"))
    out = ROOT / ".work" / "pages"
    out.mkdir(parents=True, exist_ok=True)
    for c in pend["candidates"]:
        url = c["primary"]["url"]
        pages, raw_main = [], ""
        rec, raw = fetch(url)
        pages.append(rec)
        if raw and "github.com" not in url and "huggingface.co" not in url:  # HF pages only link to HF's own navigation; the vendor's blog is found via the model card below
            for u in hops(url, raw):
                pages.append(fetch(u)[0])
        card = hf_card_url(url)
        if card and rec.get("text"):  # the model card usually links to the vendor's release blog: that page carries the announcement and its date
            readme_links = re.findall(r"\]\((https://[^)\s]+)\)", get_safe(card))
            vendor_hosts = [u for u in readme_links if "huggingface.co" not in up.urlparse(u).netloc and re.search(r"(blog|news|announce|release|introducing)", u, re.I)]
            for u in list(dict.fromkeys(vendor_hosts))[:2]:
                pages.append(fetch(u)[0])
        (out / f"{c['entity_id']}.json").write_text(json.dumps({"entity_id": c["entity_id"], "pages": pages}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(c["entity_id"], [(p["url"][:60], p["status"]) for p in pages])


if __name__ == "__main__":
    sys.exit(main())
