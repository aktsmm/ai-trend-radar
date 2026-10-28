# 運用手順(runbook)

全自動(人のレビューなし)で回るため、止まったときに何を見るかをまとめます。

## 流れ

1. `radar`: 毎日 05:00 JST に収集・スナップショット。月曜 00:30 JST に週次レポート、木曜 00:30 JST に中間更新(掲載済みは固定し、新しい候補だけ追加)→ コミット。GitHub の定期実行は数時間遅れる・落ちることがある。
2. レポート後に `digest`(gh-aw)を起動。未処理の候補を調べ、JSON を作り、`digest_gate` を通し(失敗なら最大 5 回修正)、PR を作る。毎回、その週の全掲載項目を見直してテーマも書き直す。
3. `auto-merge-digest` が、**信頼できるコード(既定ブランチ)** で許可リスト・ゲート・テスト・ビルドを検証して自動マージ。PR のコードは実行しない。PR を開いたとき・30 分ごと(対象 PR がなければ軽い事前チェックで終了)・手動で動く。ボット作成の PR では PR 起動が発火しないことがあり、定期確認が本線。
4. `pages` がビルドして公開(`PAGES_ENABLED=true` のとき)。公開サイトの週は「掲載ありの最新週」(`analyze.weeks.site_label`)で、新しい週は digest が merge されるまで前の週のまま。
5. `watchdog`(6 時間ごと)と `daily-tests`(毎日 06:40 JST)、`token-check`(毎週月曜)が、止まり・古さ・失効を検知して Issue にする(下の「監視」)。

## 症状別

| 症状 | 見る場所 | 対処 |
| --- | --- | --- |
| サイトが更新されない | Actions: `pages` の最新実行、`about.html` の実行状況 | 失敗ならログ確認 → `workflow_dispatch` で再実行。`PAGES_ENABLED` と Pages の設定(Source: GitHub Actions) |
| 週次レポートが作られない | `radar` の最新実行、Issue「[watchdog]」 | 取得元の失敗は `api/v1/health.json` と `source_status`。落ちた定期実行は watchdog が再起動する(最後の成功から 30 時間) |
| digest の PR が来ない | `digest` の実行ログ、Issue「[digest] dropped candidates」 | `COPILOT_GITHUB_TOKEN` の失効を疑う(`token-check` の Issue)。再発行して再実行。変更なしは `noop` で PR は出ない |
| PR がマージされない | PR のコメント(原因の抜粋つき)、`auto-merge-digest` のログ | 下の「PR が止まったとき」 |
| 誤情報・無関係な項目が載った | 該当キーワードの JSON | 下の「誤掲載の訂正」 |
| 重大ニュースが載らない | `rejected_candidates.json` の却下理由、`.work/pages` に相当する取得結果 | 下の「取りこぼしの調べ方」 |
| 取得元が落ちている | `health.json`、Issue「[source-health]」 | 数日は放置してよい。恒久的ならフィードを `collect/official.py` から外す |

## PR が止まったとき

1. PR コメントの「原因(抜粋)」とログの `ERROR:` / `REJECT` 行を見る。同じ PR で 2 回失敗すると `[auto-merge]` の Issue が立つ。4 時間超で watchdog が再実行し、24 時間超で Issue にする。
2. コードかデータかを切り分ける: 新しい週のデータを手元に入れて再現する(`git checkout origin/<digest ブランチ> -- data/reports/<週>` → `python -m analyze.apply` → `python -m unittest discover -s tests`)。**確認後は data と生成物を戻し、コミットに混ぜない**。
3. 原因がコード(特定の週のデータを前提にしたテスト・検査)なら、コードを直して PR → CI → squash merge し、`auto-merge-digest` を手動実行する。
4. digest の PR が誤った却下(例: 本文が取れなかっただけ)を含むなら、merge せず閉じ、取得側を直してから `digest.lock.yml -f week=<週>` を再実行する。却下は「済み」と数えられ、その週は再調査されないため。
5. 長引く実行(`merge` ジョブの apt / Chromium 導入)は、キャンセルして再実行する(下の「CI の注意」)。

## 誤掲載の訂正

自動マージは掲載の削除を拒否する(設計の安全弁)。人が出す PR でも CI の `digest_gate` が削除を `REJECT` するため、訂正の PR は CI が赤くなる。手順:

- 該当 entity を `digest` / `slides` / `decks` / `enrichment` / `glossary` から外し、`rejected_candidates.json` に理由を書く。そのキーワードを根拠にした `themes` もないか確認する。`data/stoplist.yml` の `generic` に誤クラスタの語を足す(実在の製品名と衝突する語は足さない)。
- `python -m analyze.apply` → `python -m analyze.digest_gate` → `python -m render.build_all --offline` → テスト全件を手元で通す。
- 削除による CI の赤が意図どおりであることを確認し、管理者権限で squash merge する。master の `daily-tests` が緑に戻ることを確認する。

## 取りこぼしの調べ方

重大な発表が載らないときは、段階ごとに確認する(2026-10-28: LFM3・Kimi K3.1 Pro の事例)。

1. 収集: `data/snapshots` と各週の `report.json`(`official_ledger`、候補プール)に出ているか。公式フィードがない発表元は `collect/official.py` の `BLOG_INDEXES`(ブログ一覧のスクレイプ)と、`collect/sources.py` の `HF_ORGS`(HF 組織の新着)で拾う。HF にも自社ブログにも出ない発表は拾えない。
2. 順位: 候補になっているか。`analyze/pending.py` は公式の一次情報があるモデルを順位より先に調べる。
3. 本文の取得: `analyze/prefetch.py` が一次情報の本文を取れているか。HF のモデルページは README と、カードが指すベンダーのブログを取る。主 URL がカタログ(OpenRouter / Ollama)なら、言及リンクのうち許可リスト(`analyze/report.py` の `OFFICIAL_DOMAINS`)のドメインを `vendor_links` として取る。
4. 却下理由: `rejected_candidates.json` が「本文を確認できなかった」「一次情報がない」なら、2〜3 の取得の問題を疑う。AI の判断だけを責めない。

## 巻き戻し

誤った週次公開は、`git revert <merge commit>` を push すれば、`pages` が再ビルドして元に戻ります。

## Secret と期限

- `COPILOT_GITHUB_TOKEN`: fine-grained PAT(Copilot Requests のみ。このリポジトリに限定、**有効期限なし**)。再発行は GitHub の設定で本人認証(passkey 等)が要る。新しい値は、クリップボード経由で `gh secret set COPILOT_GITHUB_TOKEN` に渡し、チャットやログに出さない。失効・権限不足は `token-check` が週 1 回 Issue にする。
- 不要な PAT の削除は、対象の名前と ID を 1 件ずつ確認してから行う(誤って稼働中のものを消すと secret が無効になる)。
- `BRAVE_API_KEY`(任意)。値はログ・成果物に出さない。

## digest(gh-aw)の運用メモ(実際に動かして分かったこと)

- エージェントのサンドボックスには **fetch ツールも任意のシェルもない**。候補ページは実行前に `analyze.prefetch` が取得し(`.work/pages/`)、エージェントはそれだけを根拠にする。
- 許可されるシェルは `./gate.sh`(単独で実行)のみ。`cd`・`&&`・python の直接実行は拒否される。JSON の編集は edit/write ツールで行う。
- 変更があれば、エージェントが `create_pull_request` を呼ぶ(呼ばなければ PR は作られない)。何も変えなければ `noop`。
- ボットが作った PR の `ci` は承認待ち(`action_required`)になることがあるが、自動マージは `ci` に依存しない(信頼コードで同じ検査を行う)。
- ブランチ保護は force push・削除の禁止のみ(必須チェックにすると、ボットの自動マージが止まるため)。
- `digest.md` を変えたら `gh aw compile digest` で `digest.lock.yml` を再生成する。

## gh-aw の注意

- gh-aw は公開プレビューで、コンパイラのバージョンが拒否されることがある(`Blocked compile-agentic version` など)。その場合は `gh extension upgrade gh-aw` → `gh aw compile digest --strict` で `digest.lock.yml` を再生成し、`.github/aw/actions-lock.json` を更新する。
- AI の使い過ぎは `digest.md` の `max-ai-credits` / `max-daily-ai-credits` で上限をかけている。上限に達したら実行は止まり、次の週次で再開する。

## 自動マージの安全境界

- PR から取り込むのは `data/reports/<週>/{enrichment,digest,slides,decks,themes,glossary,rejected_candidates}.json` のみ。他のパスが 1 つでもあれば取り込まない。
- `data/trends.json` と `site/data.js` は信頼せず、信頼コードで再生成して PR の内容と一致することを要求する。
- `--match-head-commit` で、検証後に PR が更新された場合はマージしない。
- 掲載の削除と、1 回あたりの変更件数の上限(6)はゲートが拒否する。
- ゲートは形式・出典・日付の整合・中身のない要約の排除までで、本文の事実誤りは検出できない。サイトに「AI の下書きを一次情報と照合」の注意書きを常時表示し、誤りは GitHub Issue で受け付ける。

## 監視

- `watchdog`: 75 分超の digest 実行のキャンセル、失敗した pages の再実行、失敗した digest の 1 回再 dispatch(2 回連続で Issue)、digest PR の再確認、Pages の再デプロイ(master が最後の公開より新しいとき)、公開サイトのデータ時刻が master より 3 日以上遅れたとき Issue、radar の最後の成功から 30 時間で再起動、9 日成功がないとき Issue。
- `daily-tests`: master で `digest_gate`・ビルド・全テスト。失敗すると Issue を作り、回復すると閉じる。収集元の健全性(`analyze.source_health`)は `[source-health]` Issue に分け、フルテストを赤にしない。
- `analyze.source_health`: 公式フィード・ブログ一覧が直近 3 週ずっと 0 件、または最新の週で取得に失敗したものを検出する。たまにしか出さない発表元は `QUIET_OK` で除外し、コードから外した収集元・追加直後のものは判定しない。
- `token-check`: 毎週月曜、`COPILOT_GITHUB_TOKEN` の有効性と期限を確認する。

## CI の注意

- フォント導入(apt)と `playwright install --with-deps` は、GitHub 側のミラーが固まって実行が 20 分以上止まることがある。1 回 120〜240 秒の上限、3 回までの再試行、ステップ全体 6〜10 分の上限を付け、自動マージのジョブ全体は 25 分で打ち切る。上限で落ちたら手動で再実行する。
- ワークフローの YAML を直したら `python -c "import yaml; yaml.safe_load(open('<file>', encoding='utf-8'))"` で構文を確認する(`name:` の値にコロンがあると壊れる)。
- 生成物(`data/trends.json`、`site/data.js`、`data/reports/*/enrichment.json`)が master と衝突したときは master 側を取り、コードの差分だけを残す。

## 収集・データの注意

- `collect.common.get` は gzip のまま返る応答を展開する(Google DeepMind のフィードが 2 週間、gzip のまま返って解析に失敗していた)。
- `hf_models` は、トレンド上位 60 件に加えて、主要ベンダーの HF 組織の直近の新着(likes 25 以上)も取る。
- 公式のブログ一覧スクレイプは、記事ページの公開日(`article:published_time`、`datePublished`、`<time>`、最後の手段として `dateModified` と本文の「Month D, YYYY」)で窓内かを判定する。
- 公開サイトの前の週・次の週の動線は `site/app.js` が `api/v1/index.json` の `weeks` から作る(読めないときは非表示)。

## テストの書き方(週のデータに依存させない)

- 最新週のデータ(`data/trends.json`)は毎週変わり、掲載が 1〜数件のこともある。テストで特定のキーワード、件数、kind の分布を前提にしない。
- 絞り込みなど複数件が要る確認は、`analyze.weeks.archive_weeks()` から条件に合う週を選ぶ(例: `tests/test_gated_download.py`)。固定の週(2026-W42)を読む既存のテストはそのままでよい。
- 「まだ要約がない新しい週」の状態でもゲート・ビルド・テストが通ること(`tests/test_site_label.py`)。
- 手書きの 4 ページ(index / about / archive / glossary)は、h1 が 1 つ、本文へ移動のスキップリンク、12px 未満の文字なし、を `tests/test_a11y.py` で守る。ページを足したら同じ形(h1・skip・`id` 付きの main)にする。

