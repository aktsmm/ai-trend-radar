# JSON API(静的)

GitHub Pages から配信する、読み取り専用の静的 JSON です。認証は不要で、CORS は `*` で利用できます(ブラウザ、Power Automate、スクリプトから `GET` できます)。生成は `python -m render.build_api`(`render.build_site` から自動実行)。

ベース URL(公開後): `https://<owner>.github.io/ai-trend-radar/`

## エンドポイント(`api/v1/`)

| パス | 内容 |
| --- | --- |
| `api/v1/index.json` | バージョン、取得時点、週の一覧、エンドポイントとダウンロードの URL テンプレート、注意書き |
| `api/v1/latest.json` | 最新の週の掲載項目(軽量) |
| `api/v1/weeks/<週>.json` | 週ごとの掲載項目・テーマ・公式発表(掲載のあった全ての週) |
| `w/<週>/index.html` ほか | 過去週のページと成果物(`assets/`、`downloads/` を含む)。最新週はルートにある |
| `api/v1/keywords/<id>.json` | 1 件の詳細。ダイジェスト、図解、ブリーフ(deck)、確認記録、話題の根拠 |
| `api/v1/categories/<category>.json` | カテゴリ別の軽量索引 |
| `api/v1/candidates.json` | 観測候補(未掲載)と見送りの理由 |
| `api/v1/themes.json` | 今週の共通テーマと背景の見立て(解釈。signals で各項目の根拠、refs で出典を示す) |
| `api/v1/highlights.json` | 今週の公式発表(タイトル・発表元・日付・URL のみ。要約なし) |
| `api/v1/health.json` | 取得元の成否、件数。監視用 |
| `enc/<id>.json` | **暗号化された**ブリーフ(2 枚)。サイトの「ダウンロード」でパスワードを入れたときだけ、ブラウザ内で復号して PDF / PowerPoint にします(直接は読めません) |
| `assets/slides/<id>.png` | 図解(1 キーワード 1 枚) |
| `downloads/trends.json` | 週次レポート全体(内部形式。安定性は保証しない) |

任意条件の絞り込みや全文検索の API はありません(静的ファイルのため)。個別ファイルを取得して、クライアント側で絞り込んでください。

## 項目(light)のフィールド

`id`、`keyword`、`headline`(カードの見出し)、`vendor`、`category`、`kind`、`tags`、`rank`、`score`、`summary`(概要の配列)、`published_at`(一次情報の公開日時)、`official_urls`、`verification`(`status`: verified / partially_verified / unverified、`checked_at`)、`urls`(関連ファイルの相対パス)。

`keywords/<id>.json` には、上に加えて `digest`(`why_trending` / `what_changes` / `benefits` / `caveats` / `audience`)、`infographic`、`deck`(`overview` / `impact` / `sources`)、`verification.checks`、`mentions`、`jp_reactions` が入ります。

## 安定性とバージョン

- フィールドの追加は同じバージョン内で行います。削除・意味の変更は `api/v2/` を新設します。
- 要約・図解・ブリーフは AI の下書きを一次情報と照合したものです。ベンダー発表の数字は独自には検証していません。`verification.status` が `unverified` の項目は掲載されません(`candidates.json` のみ)。
- 週が変わると `latest.json` は新しい週に切り替わります。
