# AI Trend Radar (ローカルモック v2)

過去7日間に「新しく出たもの」(製品・モデル・リリース・論文・ハード)を機械的に集め、**一次ソース(公式発表/リリースノート/公式GitHub Release)で裏取りできたものだけ**を週次TOP20として出す。将来は1件2〜3枚の初心者向けスライドを付ける(今回はTOP20生成まで。サンプル: `slides/strata-1.pptx`)。

```
pip install -r requirements.txt
python -m collect.run              # 日次: 取得 -> data/raw(artifact), data/snapshots(artifact), 失敗は台帳に記録
python -m analyze.report [--week 2026-W42]   # 週次レポート -> data/reports/YYYY-Www/report.json, data/trends.json, site/data.js
python -m analyze.validate         # schema/trend.schema.json で検証
python -m unittest discover -s tests         # 固定fixtureでの決定性・ゲート・X障害時の順位安定テスト
# site/index.html をブラウザで開く(カテゴリフィルタ付き一覧)
```

## 仕組み(v2)

1. **粒度**: 候補は製品/モデル/リリース/論文/ハードのみ。ベンダー名・一般概念(RAG, MoE, ChatGPT 等)は `data/stoplist.yml` でTOPから除外。
2. **一次ソース**: 公式フィード許可リスト(OpenAI/Google/NVIDIA/AWS/Microsoft/Hugging Face/Qwen/Ollama/Mistral/Anthropic(HTML解析)と、公式repoのGitHub Releases)。エンティティはタイトルに主題として出ること(本文の言及のみは不可)。公開日がJST週(半開区間)内でないものは「保留」。
3. **話題性**: Reddit/HN/Lobsters/dev.to/Bluesky/HF/GitHub から、ソース横断スコア+投稿数+リリース頻度+HN前週比(常連の減点)。X補助スコアは上限+0.5。
4. **X**: `/2/search` は2026-10-09から404(FxEmbed #2303)。毎回1回だけ試行→スキップ記録。代わりに公式/キーパーソン12アカウントのウォッチリスト(`config/x_watchlist.yml`)から投稿を取り、公式サイトへのリンク付き投稿は「未検証リード」として別枠表示(採用には公式裏取り必須)。HN/Reddit内のX URLは `/2/status` で補完。Brave `site:x.com` は `BRAVE_API_KEY` があるときのみ(未検証)。
5. **枠管理**: カテゴリ(model / dev-tool / local-runtime / hardware / research / github-trending)の枠で選抜。同週・同ベンダー・同カテゴリは最も根拠の強い1件に統合(`related`)。GitHub由来は説明可能ルール(fork/archived/説明なし/宣伝語/同一作者大量repo/異常な週間スター)で品質判定。
6. **新顔の解決**: HN/Redditにしか名前が無い新語は、`owner/Name` 言及またはGitHub検索で公式repoを特定し、その repo の **Releases(公式リリース)** を一次ソースにする(例: Strata)。
7. **データ層**: 日次スナップショット(`metric_semantics` 付き)。14日分たまるまでは `baseline`(「上昇中」と呼ばない)。Gitに入れるのは週次レポート・fixture・設定のみ。詳細は [docs/sources.md](docs/sources.md)。

## 今週のTOP20(rolling 7日 / 2026-10-15 時点, baseline)

| # | キーワード | カテゴリ/種別 | スコア | 一次ソース(種別・公開日) |
|---|---|---|---|---|
| 1 | Claude Code | dev-tool / release | 100.0 | [release_note](https://github.com/anthropics/claude-code/releases/tag/v2.1.300) 2026-10-14 |
| 2 | OpenAI Codex | dev-tool / product | 97.9 | [announcement](https://openai.com/index/oracle) 2026-10-08 |
| 3 | Ollama | local-runtime / product | 94.4 | [announcement](https://ollama.com/blog/fly-io-sprites) 2026-10-13 |
| 4 | Qwen-Image-2.1 | model / model | 89.5 | [model_card](https://huggingface.co/Qwen/Qwen-Image-2.1-Turbo) 2026-10-09 |
| 5 | llama.cpp | local-runtime / release | 88.7 | [release_note](https://github.com/ggml-org/llama.cpp/releases/tag/b11624) 2026-10-14 |
| 6 | vLLM | local-runtime / release | 67.5 | [release_note](https://github.com/vllm-project/vllm/releases/tag/v0.32.0rc0) 2026-10-12 |
| 7 | lfm2 | model / model | 53.3 | [model_card](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B) 2026-10-12 |
| 8 | Unsloth | local-runtime / release | 48.6 | [release_note](https://github.com/unslothai/unsloth/releases/tag/prebuilt-wheels-cu13) 2026-10-14 |
| 9 | gemini-4-argon | model / model | 48.5 | [announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/) 2026-10-13 |
| 10 | GitHub Copilot | dev-tool / product | 45.5 | [release_note](https://github.blog/changelog/2026-10-13-gemini-4-argon-in-github-copilot) 2026-10-13 |
| 11 | Open WebUI | local-runtime / release | 42.4 | [release_note](https://github.com/open-webui/open-webui/releases/tag/v0.12.2) 2026-10-14 |
| 12 | Strata | local-runtime / release | 41.9 | [release_note](https://github.com/Niko1221/Strata/releases/tag/v0.1.44) 2026-10-14 |
| 13 | JEV | model / model | 40.6 | [model_card](https://huggingface.co/autotrust/JEV-35B-NVFP4) 2026-10-11 |
| 14 | MLX | local-runtime / release | 37.8 | [release_note](https://github.com/ml-explore/mlx/releases/tag/v0.32.4) 2026-10-14 |
| 15 | ARTEX | dev-tool / product | 36.7 | [repo](https://github.com/mhtsec/ARTEX) 2026-10-08 |
| 16 | SageMaker | dev-tool / product | 35.7 | [release_note](https://aws.amazon.com/about-aws/whats-new/2026/10/sagemaker-studio-social-sign-in/) 2026-10-14 |
| 17 | clef | model / model | 35.5 | [model_card](https://huggingface.co/Cloudflare/clef-omni) 2026-10-09 |
| 18 | talorys | dev-tool / release | 34.7 | [release_note](https://github.com/rociiu/talorys/releases/tag/create-talorys%400.1.6) 2026-10-13 |
| 19 | Grok 4.7 | model / model | 32.7 | [announcement](https://aws.amazon.com/blogs/machine-learning/build-long-horizon-agents-with-grok-4-7-on-amazon-bedrock/) 2026-10-13 |
| 20 | AgentCore | dev-tool / product | 32.5 | [announcement](https://aws.amazon.com/blogs/machine-learning/build-self-improving-document-processing-using-amazon-bedrock-agentcore/) 2026-10-14 |

## 既知の課題

- 「リリース」系(Claude Code, llama.cpp 等)は常にリリースがあるため上位に来やすい。14日分のスナップショットがたまるまで「上昇」は判定できない(baseline表示)。
- hardware / research / github-trending は今週は条件を満たす候補が少なく0件(枠は他カテゴリで補充)。
- 公式ソース未対応: Google DeepMind(HTML)、Meta AI(400)、DeepSeek(社内ITポリシーでブロックのため収集しない)。
- ARTEX/talorys など小規模GitHub由来の品質は説明可能ルールのみで判定(人手確認が必要)。
- 要約・日本語化・曖昧エンティティ判定のLLM工程は未実装(フェーズ2)。
