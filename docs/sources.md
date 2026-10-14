# ソース台帳 (docs/sources.md)

2026-10-15 実測。各 collector は独立して失敗し、失敗は `data/raw/_status.json` / `_official_ledger.json` に記録して処理を続行する。
生データ(`data/raw/`)と日次スナップショット(`data/snapshots/`)は Git に積まず、CI の artifact(保持期限付き)で保管する。

| ソース | 方式 | 認証 | 利用条件 | 保存量/日 | 失敗時 / バックオフ | 日次上限の目安 |
|---|---|---|---|---|---|---|
| Hugging Face models/spaces/daily_papers | API | 不要 | [HF Hub API](https://huggingface.co/docs/hub/api) | 約0.2MB | スキップ+記録 | 3 req |
| GitHub Search / repos / releases.atom | API / Atom | 任意(`GITHUB_TOKEN`、ローカルは `gh auth token`) | [REST API](https://docs.github.com/rest) | 約0.5MB | 403/429でスキップ。未認証は10〜60 req/h | 〜80 req(要トークン) |
| GitHub Trending | HTML | 不要 | 公式APIなし。HTML構造変更で壊れる | 数十KB | 0件ならエラー記録 | 1 req |
| Hacker News (Algolia) | API | 不要 | [HN Search API](https://hn.algolia.com/api) | 約0.3MB | クエリ単位でスキップ。velocity計測は〜300 req | 〜350 req |
| Reddit RSS (r/LocalLLaMA, r/ollama, r/MachineLearning) | RSS | 不要(ブラウザUA) | `.json` は403。RSSは並列で429 → 直列+2秒待機+リトライ | 約0.3MB | 429は記録してスキップ(r/ollama等が不安定) | 3 req |
| Lobsters / dev.to / arXiv / Bluesky(api.bsky.app) | API | 不要 | 各サービス規約に従い低頻度 | 約0.5MB | スキップ+記録 | 〜20 req |
| Ollama library / OpenRouter models / PyPI Stats | HTML / API | 不要 | HTML構造変更に注意 | 数十KB | スキップ+記録 | 〜15 req |
| FxTwitter `/2/status/{id}` | API(第三者) | **渡さない** | X社非公式。`/2/search` は2026-10-09夜から404([FxEmbed #2303](https://github.com/FxEmbed/FxEmbed/issues/2303))。毎回1回だけ試行→404なら6時間クールダウン | 数KB | 失敗してもTOPは不変(テスト済) | 〜50 req |
| FxTwitter `/2/profile/{handle}/statuses` | API(第三者) | 渡さない | `config/x_watchlist.yml`(所有者確認済み公式/キーパーソン12件)を5並列、返信/リポスト除外、最終取得IDを保存 | 〜0.1MB | アカウント単位で記録 | 12 req |
| Brave Search `site:x.com` | API | `BRAVE_API_KEY`(任意) | キー無しは未実行と記録 | - | キー無し=スキップ | 〜30 req |

## 公式発表ソース(許可リスト制) 実測

`collect/official.py` の `FEEDS` / `GH_REPOS` が許可リスト。`source_type` は announcement / release_note を保持する。

| 結果 | ソース |
|---|---|
| OK(RSS/Atom) | OpenAI news, Google AI blog, NVIDIA blog / developer blog, AWS ML blog / What's New, Microsoft Foundry blog, GitHub changelog, Hugging Face blog, Qwen blog, Ollama blog, Mistral news(`/news/rss`) |
| OK(HTML解析) | Anthropic news(RSSなし。`/news` 一覧の日付・タイトルを解析) |
| OK(GitHub Releases) | ggml-org/llama.cpp, ollama/ollama, vllm-project/vllm, sgl-project/sglang, anthropics/claude-code, openai/codex, google-gemini/gemini-cli, QwenLM/Qwen3, huggingface/transformers, ml-explore/mlx, unslothai/unsloth, open-webui/open-webui, modelcontextprotocol/servers, microsoft/autogen, github/copilot-cli |
| 失敗 | Google DeepMind blog(XMLではなくHTMLを返す→未対応), Meta AI blog(HTTP 400) |
| 対象外 | Microsoft AI blog(HTTP 410 廃止)。**DeepSeek公式サイトは社内ITポリシーでブロックされるため収集しない**(GitHub Releaseの`deepseek-ai/DeepSeek-V3`のみ) |

ledger の最新値は `data/raw/_official_ledger.json`(CI artifact)。

## データ層の約束

- 週の定義: JST の半開区間 `[月曜00:00, 翌月曜00:00)`。イベントは公開日で所属週を決める(`--week YYYY-Www` で再処理可能)。省略時は直近7日(`partial=true`)。
- `metric_semantics`: 同一repoの総スター差分=差分可能 / GitHub Trendingの週次スター=明示値 / HF trendingScore等=順位観測のみ / 公式発表・リリース=イベント。欠損は unknown。
- 日次スナップショットが14日分たまるまでは `baseline` 表示(「上昇中」と呼ばない)。
- 失敗した実行は既存の公開物(`data/reports/*`, `site/data.js`)を上書きしない(レポート生成が例外終了すると書き込み前に停止)。
