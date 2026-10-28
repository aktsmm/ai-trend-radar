"""Shared helpers: HTTP, time window, raw-data persistence."""
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(days=7)
SINCE_TS = int(SINCE.timestamp())
SINCE_DATE = SINCE.strftime("%Y-%m-%d")

X_URL_RE = re.compile(r"https?://(?:www\.|mobile\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/status(?:es)?/(\d{5,25})")


def get(url, headers=None, timeout=25, retries=1):
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(headers or {})
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if body[:2] == b"\x1f\x8b":  # some servers gzip the body even though Accept-Encoding was not sent
                    import gzip
                    body = gzip.decompress(body)
                return body.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429 and i < retries:
                time.sleep(5 * (i + 1))
                continue
            break
        except Exception as e:  # network / timeout
            last = e
            time.sleep(1)
    raise last


def get_json(url, headers=None, **kw):
    return json.loads(get(url, headers, **kw))


def item(source, title, url="", text="", metric=0.0, metric_name="", rank=None, created=None, **extra):
    d = {"source": source, "title": (title or "").strip(), "url": url, "text": (text or "").strip()[:2000],
         "metric": float(metric or 0), "metric_name": metric_name, "rank": rank, "created": created}
    d.update(extra)
    return d


def save_raw(name, data):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def extract_x_urls(*texts):
    out = []
    for t in texts:
        for m in X_URL_RE.finditer(t or ""):
            u = f"https://x.com/{m.group(1)}/status/{m.group(2)}"
            if u not in out:
                out.append(u)
    return out
