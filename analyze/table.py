"""Print the TOP table as Markdown (for README)."""
import json

from collect.common import ROOT

t = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
print("| # | キーワード | カテゴリ/種別 | スコア | 一次ソース(種別・公開日) |\n|---|---|---|---|---|")
for e in t["trends"]:
    p = e["primary"]
    print(f"| {e['rank']} | {e['keyword']} | {e['category']} / {e['kind']} | {e['score']} | [{p['source_type']}]({p['url']}) {(p['published_at'] or '')[:10]} |")
