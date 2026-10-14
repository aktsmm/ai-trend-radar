# AI Trend Radar (ローカルモック)

過去7日間の AI / ローカルLLM 界隈で「上昇中のキーワード」を複数ソースから機械的に集め、ソース横断スコアで TOP を出す実現可否検証。
将来は azure-update-digest のように、キーワードごとに初心者向けスライド(2〜3枚)・分野タグ・公式URL付きで公開する想定(pptx生成は未着手)。

```
python -m collect.run        # 取得 -> data/raw/*.json, data/raw/_status.json(失敗ソースは記録してスキップ)
python -m analyze.build      # キーワード抽出+スコア+X補完 -> data/trends.json, site/data.js
python -m analyze.validate   # schema/trend.schema.json で検証(要 jsonschema)
# site/index.html をブラウザで開く(タグフィルタ付き一覧)
```
依存: 標準ライブラリのみ(検証のみ `jsonschema`)。任意の環境変数: `GITHUB_TOKEN`(レート緩和), `BRAVE_API_KEY`(X検索)。

## 取得元の可否(2026-10-15 実測)

| 分野 | ソース | 結果 | 備考 |
|---|---|---|---|
| models | Hugging Face models/spaces trendingScore | OK | |
| research | HF daily_papers / arXiv / r/MachineLearning | OK | |
| tools | GitHub Search(created:>日付, 複数クエリ) / Trending HTML / PyPI Stats | OK | 未認証はSearchが10req/分 |
| community | Hacker News(Algolia) / Lobsters / dev.to / Bluesky(api.bsky.app) | OK | |
| local-llm | r/LocalLLaMA RSS(週間TOP) / Ollama library(newest) | OK | Reddit .json は403。RSSはブラウザUA必須で429が出やすく、直列+リトライで対処 |
| local-llm | r/ollama RSS | 不安定 | 429で失敗することがあり、その場合はスキップを記録 |
| vendor | OpenRouter /api/v1/models(新規モデル) | OK | 公式ブログRSS等は未実装(今後の追加候補) |
| X | FxTwitter `/2/status/{id}` | OK(既知URLのみ) | 検索 `/2/search` は404。認証情報は渡さない |
| X | Brave Search `site:x.com` | **未検証** | `BRAVE_API_KEY` 未設定のためスキップ(`x_integration.brave` に記録)。実装済み |

## スコア方式

1. 各ソースのアイテム強度を 0〜1 に正規化(指標あり: `log1p(値)/log1p(ソース内最大)`、順位のみ: `1-(順位-1)/N`、存在のみ: 0.3)。
2. キーワード×ソースで `最大 + 0.25×次点3件合計`(上限1.5)にソース重み(HN/Reddit/HF models/Trending=1.0 … arXiv=0.3)を掛けて合算。
3. 分野の異なるソースに跨るほど加点(+0.25/分野)。
4. **X補助スコア**(最大 +0.5): HN/Reddit/Lobsters/dev.to/Bluesky の本文・リンクから抽出した x.com status URL を FxTwitter で補完し、投稿本文にキーワードが含まれるものだけ likes+2×reposts+views/200 の対数で加点。Xの数値は候補発見・補助のみで、採用は本文と外部リンク先(repo/公式)で確認する方針。
5. 最大値を100に正規化。

候補は (a) 固有名詞辞書 `analyze/lexicon.py`(タグ・公式URL付き)、(b) HF/Ollama/OpenRouter/GitHub/論文タイトルから動的抽出(量子化・サイズ等のノイズ語を除去)、(c) HN等のタイトルから頻出する型番風名称。
偏り抑制: 主タグごと最大4件、同一ベンダー最大2件。複数ソース一致(または単独でも十分強い)ものだけ採用。

## 今週のTOP20(`data/trends.json`)

| # | キーワード | タグ | スコア | ベンダー | 一致ソース数 |
|---|---|---|---|---|---|
| 1 | Claude Code | agents, tools | 100.0 | Anthropic | 6 |
| 2 | OpenAI | vendor, models | 97.7 | OpenAI | 8 |
| 3 | Qwen3 | models, local-llm, hardware | 92.2 | Alibaba | 7 |
| 4 | DeepSeek | models, local-llm, hardware | 86.2 | DeepSeek | 8 |
| 5 | Qwen-Image-2.1 | models, local-llm | 80.6 | Alibaba | 5 |
| 6 | JEV | models, local-llm | 77.9 | - | 7 |
| 7 | MCP | agents, tools, research | 77.0 | Anthropic | 8 |
| 8 | GGUF | local-llm, tools, hardware | 75.2 | ggml | 7 |
| 9 | Quantization | local-llm, research, hardware | 65.7 | - | 7 |
| 10 | glm-5.3 | local-llm, models | 64.6 | Zhipu | 5 |
| 11 | OpenAI Codex | agents, tools | 64.0 | OpenAI | 5 |
| 12 | Ollama | local-llm, tools, hardware | 59.1 | Ollama | 6 |
| 13 | Mixture of Experts | research, models, hardware | 53.7 | - | 5 |
| 14 | RAG | tools, research | 53.1 | - | 8 |
| 15 | ChatGPT | tools, local-llm | 51.2 | - | 6 |
| 16 | OpenCode | agents, tools | 49.1 | OpenCode | 5 |
| 17 | MiniCPM | tools, local-llm | 45.7 | - | 4 |
| 18 | Hugging Face | vendor, tools | 40.7 | HuggingFace | 4 |
| 19 | NVIDIA DGX Spark | hardware, local-llm | 38.2 | NVIDIA | 3 |
| 20 | Apple Silicon | hardware, local-llm | 29.6 | Apple | 3 |

上位3件(Claude Code / OpenAI / Qwen3)は公式URLの到達確認済みで、スライド案(2〜3枚)を `data/curated.json` に記載し一覧ページに表示。それ以外の `official_urls` は辞書URLまたはHF/GitHub等の一次ページで、`official_verified` が false のものは未確認。
X連携の実績: 取得データ内のX URL 8件を FxTwitter で補完(全件成功)。

## 課題・所感

- 取得は約1〜2分・認証不要でほぼ全ソース成立。ソース多様性は確保できた。
- 「OpenAI」「RAG」等の一般語/概念が上位に来やすい。固有名詞の粒度(製品/モデル/概念)の分離、公式ブログRSSの追加、LLMによる要約・正規化が次の課題。
- 一部の新規GitHubリポジトリはスター水増し・低品質(例: ARTEX系)が混ざるため、本文・リンク先確認(または除外ルール)が必要。
- Bluesky/Xは言及数が少なく、補助指標に留めるのが妥当。
