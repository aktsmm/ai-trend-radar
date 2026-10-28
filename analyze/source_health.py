"""Source health: official feeds / blog indexes that returned nothing in every recent week, or failed in the latest one.

python -m analyze.source_health            # prints findings, exit 1 when there are any

A feed that silently turns into 0 items (the site changed its markup) looks "ok" in the collection ledger, so this compares recent weeks.
"""
import json
import sys

from collect.common import ROOT

WEEKS = 3
# feeds that legitimately publish rarely: they are only reported when they fail, never for being quiet
QUIET_OK = {"minimax-news", "together-blog", "deepmind-blog", "google-ai-blog", "meta-newsroom", "apple-ml-research"}


def findings():
    reports = sorted((ROOT / "data" / "reports").glob("*/report.json"))[-WEEKS:]
    ledgers = [json.loads(p.read_text(encoding="utf-8")).get("official_ledger", {}) for p in reports]
    if not ledgers:
        return []
    out = []
    from collect import official as O
    current = {f[0] for f in O.FEEDS} | {b[0] for b in O.BLOG_INDEXES} | {r[0] for r in O.GH_REPOS}  # sources retired from the code are not judged
    for fid, led in ledgers[-1].items():
        if fid not in current:
            continue
        if led.get("ok") is False:
            out.append(f"{fid}: 最新の週で取得に失敗 ({led.get('error', '')[:80]})")
        elif len(ledgers) == WEEKS and fid not in QUIET_OK and all(l.get(fid, {}).get("count", 0) == 0 for l in ledgers):
            out.append(f"{fid}: 直近 {WEEKS} 週ずっと 0 件(ページの構造が変わった可能性)")
    return out


def main():
    f = findings()
    for x in f:
        print("SOURCE", x)
    print(f"{len(f)} source problem(s)")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
