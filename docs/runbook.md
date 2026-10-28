# 運用手順(runbook)

全自動(人のレビューなし)で回るため、止まったときに何を見るかをまとめます。

## 流れ

1. `radar`(毎日 05:00 JST に収集・スナップショット。月曜 00:30 JST に週次レポート、木曜 00:30 JST に中間更新)→ コミット。
2. 週次レポート後に `digest`(gh-aw)を起動。未処理の候補を調べ、JSON を作り、`digest_gate` を通し(失敗なら最大 5 回修正)、PR を作る。
3. `auto-merge-digest` が、**信頼できるコード(既定ブランチ)** で許可リスト・ゲート・テスト・ビルドを検証して自動マージ。PR のコードは実行しない。
4. `pages` がビルドして公開(`PAGES_ENABLED=true` のとき)。
5. `watchdog`(6 時間ごと)が、止まった実行のキャンセル、pages の再実行、9 日成功がないときの Issue 作成を行う。

## 症状別

| 症状 | 見る場所 | 対処 |
| --- | --- | --- |
| サイトが更新されない | Actions: `pages` の最新実行 | 失敗ならログ確認 → `workflow_dispatch` で再実行。`PAGES_ENABLED` と Pages の設定(Source: GitHub Actions) |
| 週次レポートが作られない | `radar` の最新実行、Issue「[watchdog]」 | 取得元の失敗は `api/v1/health.json` と `source_status`。再実行は `radar` を手動実行 |
| digest の PR が来ない | `digest` の実行ログ、Issue「[digest] dropped candidates」 | Secret `COPILOT_GITHUB_TOKEN` の期限切れが最多。再発行して再実行 |
| PR がマージされない | PR のコメント(自動検証の失敗)、`auto-merge-digest` のログ | ゲートの `REJECT` 行を確認。データ不備ならその実体を `rejected_candidates.json` に移すか手で直す |
| 誤情報が載った | 該当キーワードの JSON | `data/reports/<週>/` から該当実体を削除(または `rejected_candidates.json` に移動)して push → 自動で再公開 |
| 取得元が落ちている | `health.json`、サイトのフッター | 数日は放置してよい。恒久的ならフィードを `collect/official.py` から外す |

## 巻き戻し

誤った週次公開は、`git revert <merge commit>` を push すれば、`pages` が再ビルドして元に戻ります。

## Secret と期限

- `COPILOT_GITHUB_TOKEN`: fine-grained PAT(Copilot Requests のみ。このリポジトリに限定、有効期限 30 日)。**期限が切れると digest が止まる**ので、期限の 1 週間前に再発行して Secret を更新する(watchdog の Issue でも気づける)。
- `BRAVE_API_KEY`(任意)。
- 値はログ・成果物に出さない。

## digest(gh-aw)の運用メモ(実際に動かして分かったこと)

- エージェントのサンドボックスには **fetch ツールも任意のシェルもない**。そのため、候補ページは実行前に `analyze.prefetch` が取得し(`.work/pages/`)、エージェントはそれだけを根拠にする。
- 許可されるシェルは `./gate.sh`(単独で実行)のみ。`cd`・`&&`・python の直接実行は拒否される。JSON の編集は edit/write ツールで行う。
- 変更があれば、エージェントが `create_pull_request` を呼ぶ(呼ばなければ PR は作られない)。何も変えなければ `noop`。
- `auto-merge-digest` は digest の完了時(`workflow_run`、**ワークフロー名で指定**)と 3 時間ごとに動く。ボットが作った PR の `ci` は承認待ち(`action_required`)になることがあるが、自動マージは `ci` に依存しない(信頼コードで同じ検査を行う)。
- ブランチ保護は force push・削除の禁止のみ(必須チェックにすると、ボットの自動マージが止まるため)。

## gh-aw の注意

- gh-aw は公開プレビューで、コンパイラのバージョンが拒否されることがある(`Blocked compile-agentic version` など)。その場合は `gh extension upgrade gh-aw` → `gh aw compile digest --strict` で `digest.lock.yml` を再生成し、`.github/aw/actions-lock.json` を更新する。
- AI の使い過ぎは `digest.md` の `max-ai-credits` / `max-daily-ai-credits` で上限をかけている。上限に達したら実行は止まり、次の週次で再開する。

## 自動マージの安全境界

- PR から取り込むのは `data/reports/<週>/{enrichment,digest,slides,decks,themes,rejected_candidates}.json` のみ。他のパスが 1 つでもあれば取り込まない。
- `data/trends.json` と `site/data.js` は信頼せず、信頼コードで再生成して PR の内容と一致することを要求する。
- `--match-head-commit` で、検証後に PR が更新された場合はマージしない。
- ゲートは形式・出典・日付の整合までで、本文の事実誤りは検出できない。サイトに「AI の下書きを一次情報と照合」の注意書きを常時表示し、誤りは GitHub Issue で受け付ける。

## 運用ガード(姉妹サイトから取り入れ)

- token-check.yml: 毎週月曜 09:20 JST に COPILOT_GITHUB_TOKEN の有効性と期限(14 日前)を確認し、問題があれば Issue を作る。回復すると自動で閉じる。
- watchdog.yml: digest が失敗したら 1 回だけ再 dispatch、2 回連続失敗は Issue にする。
- radar.yml: データ commit の push は rebase して最大 4 回リトライ。
- digest_gate: 中身のない要約(定型句、重複、短すぎる行)を reject する。


- site/about.html: しくみと実データの運用状況(health.json と GitHub Actions の直近の実行を表示)。トップのステータスバーは同じ情報の要約。


- 公開サイトの週は「掲載ありの最新週」(analyze.weeks.site_label)。radar が新しい週を master に入れても、digest が自動マージされるまでサイトは前の週のまま。digest_gate は要約がない週では何も検査せず成功する。
- watchdog は 4 時間以上 open の digest PR で auto-merge を再実行し、24 時間以上で Issue を作る。master が最後の公開より新しければ Pages を再デプロイする。


- daily-tests.yml: 毎日 06:40 JST に master で digest_gate・ビルド・全テストを実行。失敗すると Issue を作り、回復すると閉じる。


## テストの書き方(週のデータに依存させない)

- 最新週のデータ(`data/trends.json`)は毎週変わり、掲載が 1〜数件のこともある。テストで特定のキーワード、件数、kind の分布を前提にしない。
- 絞り込みなど複数件が要る確認は、`analyze.weeks.archive_weeks()` から条件に合う週を選ぶ(例: `tests/test_gated_download.py`)。固定の週(2026-W42)を読む既存のテストはそのままでよい。
- 自動マージの検証が落ちると、PR に原因(抜粋)をコメントし、同じ PR で 2 回目の失敗で Issue を作る。コード側の不整合は Issue から早く気づける。

- CI / 自動マージ / 毎日のテスト / Pages のフォント導入(apt)は、1 回 120〜180 秒の上限と 3 回までの再試行、ステップ全体 6 分の上限を付けた。apt のミラーが固まって実行が 20 分以上止まったことへの対策(2026-10-26)。自動マージのジョブ全体の上限は 25 分。

- 同じ理由で `playwright install --with-deps` も 3 回まで再試行(1 回 240 秒、ステップ全体 10 分の上限)。

- watchdog は公開サイトの `api/v1/index.json` の `data_at` と master の最新レポート時刻を比べ、3 日以上遅れていれば Issue を作る(デプロイが成功でも Pages が古いままの場合の検知。vscode-copilot-digest を参考)。

- トップと各週のページに「前の週 / 次の週 / 直近 6 週 / すべてのアーカイブ」の動線(site/app.js、api/v1/index.json の weeks から生成。読めないときは非表示でメニューのアーカイブが残る)。


- `analyze.source_health`(daily-tests で毎日実行): 公式フィード・ブログ一覧が直近 3 週ずっと 0 件、または最新の週で取得に失敗した収集元を Issue にする。ページの構造変更で黙って 0 件になるのを検知する(2026-10-28 に、Qwen のブログ停止と GitHub リリースなしのリポジトリを実際に発見して入れ替えた)。たまにしか出さない発表元は `QUIET_OK` で除外。


- 誤掲載の訂正: 自動マージは掲載の削除を拒否する(設計)。無関係な項目が載った場合は、該当 entity を digest / slides / decks / enrichment / glossary から外し、rejected_candidates.json に理由を書き、`data/stoplist.yml` の `generic` に語を足して手動で PR にする(2026-10-28: AWS IAM の話題が『Cross』という誤クラスタで載った)。

- `collect.common.get` は gzip のまま返ってくる応答を展開する。Google DeepMind のフィードが W43・W44 の 2 週間、gzip のまま返って解析に失敗していた(`analyze.source_health` が見つけた)。収集元の健全性は `[source-health]` Issue として別に通知し、フルテストを赤にしない。

