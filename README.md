# note-trend-collector

note・はてブの公開情報を整理し、発信企画を考えるためのPythonツールです。売上や再生数を予測するものではありません。

## まず、設定なしで内容見本を開く

Python 3.11以上を用意し、この修正ブランチのフォルダで実行します。見本だけなら追加ライブラリ、Gmail、APIキーは不要です。

```sh
python preview.py --output-dir preview_output
```

`preview_output/sample_report.html` をブラウザで開いてください。同じ場所に `sample_report.txt` もできます。macOS等でPythonを `python3` として使う環境では、コマンドの `python` を `python3` に読み替えます。

- 同梱の架空データ5件を使う、固定文の内容見本です。実在記事や最新トレンド、実績の紹介ではありません。
- `fixture:N1` などの表示は、同梱の合成データの識別子です。実在記事へのリンクはありません。
- 外部HTTP、AI API、メール送信は行いません。環境変数や `.env` の認証情報も読み込みません。
- 反応数の0件と未取得、本文の未取得と見出し0個を分けて表示します。
- HTMLには外部画像・スクリプト・外部CSSがなく、取得後はオフラインで開けます。
- 見本と本番メールは表示形式が異なります。メール受信やAI分析の動作確認にはなりません。
- 既存ファイルは上書きしません。再作成するときは、例えば `--output-dir preview_output_2` を指定してください。

旧コマンド `python test_run.py` も、今はこの安全な見本だけを作ります。旧 `note` / `hatena` / `x` / `analyze` / `summary` / `mail` モードは引数エラーで終了し、通信・送信は行いません。

## 修正ブランチと確認範囲

配布元：https://github.com/rei2342/note-trend-collector

修正案：https://github.com/rei2342/note-trend-collector/pull/1

この版は `fix/report-safety-20260918` ブランチ用の修正候補です。mainへの統合前はmainのDownload ZIPやForkだけではこの修正版になりません。取得後、フォルダに `preview.py` があることを確認してください。

Gitを使う場合：

```sh
git clone --branch fix/report-safety-20260918 https://github.com/rei2342/note-trend-collector.git
cd note-trend-collector
python preview.py --output-dir preview_output
```

2026年9月21日の今回修正は、Python 3.12.14で40件のオフラインテストに合格。見本は追加パッケージを読み込まない `python -I -S preview.py` でも作成できました。今回変更分のPython 3.11でのテスト、本番のClaude API・Gmail送受信・定期配信は未検証です。

それ以前にはGitHub ActionsのPython 3.11・3.12で27件が成功しました（run 35412412390、commit 3ab829b8114533ec3eae3dc4dd80036d4e44f26d）。はてブRSS30件、noteマネジメントタグ49件、note記事詳細1件とブックマーク数1件の限定取得も確認されています。旧版での限定確認であり、今回の全機能・全件取得やメール配信の成功を意味しません。

## 本番で行う処理

- noteの指定タグから公開記事を取得し、公開範囲の見出し等を整理します。手動メモを読む実装ではありません。取得先の変更で動かなくなる可能性があります。
- はてブRSSをキーワードで絞り込み、設定上限内の候補についてブックマーク数を取得します。サイト全体のランキングではありません。
- 両媒体0件なら分析とメール送信を停止。片方だけ0件の場合や一部取得失敗は、取得できた範囲と制約をレポートに示します。
- 本文未取得の見出し数は未取得とし、平均から除外。取得済みで見出しがない記事だけ0個とします。
- 公開HTMLから記事全体の有料化位置は測れないため、その推定指標は出力しません。
- AI分析では観測・仮説・未確認事項を分けるよう指示します。誤りがなくなる保証ではなく、出典の確認が必要です。
- API未設定・失敗・出力打ち切りでは、AI分析ではない集計版と明示します。
- 公開記事のスキやブックマーク数から、売上や企画の成果、今週の伸びは判断できません。

## 本番の設定と実行

見本だけを見る場合、この作業は不要です。本番は追加ライブラリを導入し、送信元・宛先を自分で設定します。詳細は [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) を参照してください。

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

テストは通信・API・SMTPを代替して確認します。依存ライブラリのインストールには通常ネットワーク接続が必要です。

GitHub Actionsでは対象リポジトリの `Settings → Secrets and variables → Actions` に設定します。ローカルでは環境変数または `.env` を使います。認証情報を公開コードへ書かないでください。

| 名前 | 用途 |
| --- | --- |
| GMAIL_ADDRESS | 送信用Gmail |
| GMAIL_APP_PASSWORD | Googleのアプリパスワード |
| TO_EMAIL | 受信先。複数はカンマ区切り |
| ANTHROPIC_API_KEY | AI分析を使う場合だけ設定 |

Googleアプリパスワードの利用可否は[Googleの案内](https://support.google.com/accounts/answer/185833)で確認してください。通常のログインパスワードとは別です。

```sh
python main.py
```

このコマンドは実際に公開情報を取得し、キーがあればClaude APIを呼び、Gmailから送信します。API費用はモデルと入出力量で変わります。チャット版Claudeの契約とは別であり、無料クレジットや一定の月額を保証しません。

モデルは `CLAUDE_MODEL` 環境変数で変更できます。未指定時はコードの既定値です。Actionsで変更する場合はworkflowのenvにも設定を追加します。利用可能なモデル・費用を確認してから本番を実行してください。

既存の `Weekly Trend Report` も本番処理です。月曜00:00 UTC（09:00 JST）は起動予定で、到着時刻ではありません。`Offline regression tests` は送信しないテストです。

## 見本の安全性だけを確かめる

追加ライブラリなしで、次の7件を実行できます。

```sh
python -m unittest discover -s tests -p test_preview.py -v
```

通信・API・SMTPが呼ばれないこと、認証情報が出力されないこと、本番モジュールと`.env`を読まないこと、HTMLエスケープ、上書き防止、旧メールモードの拒否などを確認します。

## 本番運用の残りの確認

全件取得、Claudeの実出力、Gmailの到着、受信メールの表示、定期実行、記事・添付PDFとの説明一致を確認してから運用判断してください。見本を開けたことやテスト合格だけで、自動配信の導入が完了したとは扱いません。

## ライセンス

個人利用・商用利用ともに自由に使えます。再販売はご遠慮ください。
