"""Source health: official feeds / blog indexes that returned nothing in every recent week, or failed in the latest one.

python -m analyze.source_health            # prints findings, exit 1 when there are any

A feed that silently turns into 0 items (the site changed its markup) looks "ok" in the collection ledger, so this compares recent weeks.
"""
import json
import sys

from collect.common import ROOT

WEEKS = 3
# feeds that legitimately publish rarely: they are only reported when they fail, never for being quiet
QUIET_OK = {"minimax-news", "together-blog", "deepmind-blog", "google-ai-blog", "meta-newsroom", "apple-ml-research",
             "ml-explore/mlx"}  # mlx tags a release every 2-4 weeks (v0.32.4 on 2026-10-14): three quiet weeks are normal, not a markup change


def findings():
    reports = sorted((ROOT / "data" / "reports").glob("*/report.json"))[-WEEKS:]
    ledgers = [json.loads(p.read_text(encoding="utf-8")).get("official_ledger", {}) for p in reports]
    if not ledgers:
        return []
    out = []
    latest = json.loads(reports[-1].read_text(encoding="utf-8")) if reports else {}
    gw = latest.get("source_status", {}).get("github_weekly")
    if gw and gw.get("ok") is False:
        out.append(f"github_weekly: 最新の週で取得に失敗 ({gw.get('error', '')[:80]})(GitHub Trending のページ構造が変わった可能性)")
    from collect import official as O
    current = {f[0] for f in O.FEEDS} | {b[0] for b in O.BLOG_INDEXES} | {r[0] for r in O.GH_REPOS}  # sources retired from the code are not judged
    for fid, led in ledgers[-1].items():
        if fid not in current:
            continue
        if fid not in ledgers[0] and len(ledgers) > 1:  # added recently: not enough history to call it silent
            continue
        if led.get("ok") is False:
            out.append(f"{fid}: 最新の週で取得に失敗 ({led.get('error', '')[:80]})")
            continue
        msg = judge(fid, led, ledgers)
        if msg:
            out.append(msg)
    return out


def judge(fid, led, ledgers):
    """One source's verdict from its latest ledger entry (and the recent weeks' entries): a message, or None when it looks healthy."""
    redirected = _redirect_finding(fid, led)
    if redirected:
        return redirected
    if "links" in led:
        # the collector records what it saw on the index page, so a quiet source can be told from a broken one:
        # no article links at all = the markup changed; links present but nothing recent = just quiet
        return f"{fid}: 一覧ページから記事リンクを 1 件も取れません(ページの構造が変わった可能性)" if led["links"] == 0 else None
    if len(ledgers) == WEEKS and fid not in QUIET_OK and all(l.get(fid, {}).get("count", 0) == 0 for l in ledgers):
        return f"{fid}: 直近 {WEEKS} 週ずっと 0 件(ページの構造が変わった可能性)"
    return None


def _redirect_finding(fid, led):
    """The index URL we scrape ends up on a different page: the site moved or narrowed it (liquid.ai/blog -> /news/models, which listed model posts only)."""
    url, final = led.get("url"), led.get("final_url")
    if not url or not final or "links" not in led:
        return None
    norm = lambda u: u.split("#")[0].split("?")[0].rstrip("/").replace("://www.", "://")
    if norm(url) != norm(final):
        return f"{fid}: 一覧 URL が別のページへ転送されています({url} → {final})。記事の一部しか載らない一覧になっていないか確認してください"
    return None


def main():
    f = findings()
    for x in f:
        print("SOURCE", x)
    print(f"{len(f)} source problem(s)")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
