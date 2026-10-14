"""Print the TOP table as Markdown (for README)."""
import json

from collect.common import ROOT

t = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
print("| # | キーワード | タグ | スコア | ベンダー | 一致ソース数 |\n|---|---|---|---|---|---|")
for e in t["trends"]:
    print(f"| {e['rank']} | {e['keyword']} | {', '.join(e['tags'])} | {e['score']} | {e['vendor'] or '-'} | {len({s['name'] for s in e['sources']})} |")
