# 内容見本と、本番配信の設定

この文書は修正ブランチ `fix/report-safety-20260918` 用です。main未反映の間は、mainのForkだけでは修正版になりません。コード取得後に `preview.py` の存在を確認してください。

配布元：https://github.com/rei2342/note-trend-collector

修正案：https://github.com/rei2342/note-trend-collector/pull/1

## 1. 設定なしで内容見本を見る

Python 3.11以上で、取得したフォルダの中から実行します。

```sh
python preview.py --output-dir preview_output
```

`preview_output/sample_report.html` をブラウザで開きます。`sample_report.txt` も出力されます。Pythonを `python3` として使う環境では読み替えてください。

この見本は架空5件の固定データと固定文です。最新トレンドでも、実際のAI分析でもありません。0件と未取得を区別して、情報の読み方を確かめるための内容見本です。本番メールとは表示が異なります。

追加ライブラリ、Gmail、APIキーは不要。外部通信・AI利用・メール送信・認証情報の読み込みはありません。ファイルが既にある場合は、`--output-dir preview_output_2` のように別の保存先を指定します。

`test_run.py` も今はこの見本への入口です。以前の `summary` や `mail` などのモードは実行しません。

## 2. 本番を検討するときだけ、ライブラリを入れる

見本だけでよければ、ここから先は不要です。

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

インストールは通常インターネット接続を使います。テスト中のHTTP・API・SMTPは代替しており、実メールは送信しません。2026年9月21日の修正はPython 3.12.14で40件合格。今回変更分をPython 3.11で再検証した結果ではありません。

## 3. 送信設定を揃える

| 設定名 | 内容 |
| --- | --- |
| GMAIL_ADDRESS | 送信元のGmailアドレス |
| GMAIL_APP_PASSWORD | そのアカウントのGoogleアプリパスワード |
| TO_EMAIL | 受信先。複数の場合はカンマ区切り |
| ANTHROPIC_API_KEY | AI分析を利用する場合だけ設定 |

GitHub Actionsは `Settings → Secrets and variables → Actions` に登録。ローカルは環境変数または `.env` を使います。`.env` は公開しないでください。Googleの通常パスワードは使いません。[アプリパスワードの利用条件](https://support.google.com/accounts/answer/185833)はアカウントによって異なります。

AI分析は従量課金です。モデル・料金・支出上限を確認します。`CLAUDE_MODEL` を指定しない場合はコードの既定値が使われます。Actionsで変更する場合はworkflowのenvにも追加してください。

## 4. 実行コマンドを区別する

| コマンド・機能 | 起きること |
| --- | --- |
| `python preview.py --output-dir preview_output` | 架空の内容見本をHTML/TXTに保存。通信なし |
| `python -m unittest discover -s tests -v` | オフライン検証。送信・課金なし |
| `python main.py` | 実収集、キーがあればAI利用、Gmail送信 |
| Actionsの `Offline regression tests` | オフライン検証 |
| Actionsの `Weekly Trend Report` | 本番の収集・分析・メール送信 |

APIが未設定、失敗、応答の途中打ち切りなら、集計版に切り替わります。メールが届いてもAI分析が成功したとは限りません。両媒体0件の場合は送信を止めます。

## 5. 本番で確認すること

- 実行ログが完了し、note・はてブの取得件数と未取得箇所を確認できる。
- 出典の記事へ戻り、内容と前提が合っている。
- AI分析か集計版かを判別できる。
- 指定した受信先でメールを開ける。表示崩れも確かめる。
- 定期実行でも届くことを、手動実行とは別に確認する。

月曜09:00 JSTは起動予定であり、到着時刻の保証ではありません。本番API・Gmail・定期配信はまだ未検証です。

## 障害は、止まった場所から確認

| 症状 | 確認すること |
| --- | --- |
| previewで既存ファイルのエラー | 別の `--output-dir` を指定する |
| previewが見つからない | 取得ブランチと現在のフォルダ |
| Actionsが開始しない | 有効状態、対象ブランチ、workflow、実行履歴 |
| ライブラリ導入に失敗 | Pythonバージョン、requirements、失敗ステップ |
| 記事0件／一部が未取得 | 接続・HTTPエラー、タグ、RSSカテゴリ、キーワード |
| 集計版になった | APIキー名、モデル、課金状況、応答エラー・打ち切り |
| SMTP認証エラー | 送信元とアプリパスワードの対応、Google側の利用可否 |
| 実行成功なのに未着 | 宛先、迷惑メール、受信制限、送信ログ |
| 内容が不自然 | 原文、取得範囲、欠損値、AIの仮説と事実の区別 |

原因を確かめずにパスワードを作り直す必要はありません。問い合わせでは実行日時と失敗ステップを示し、認証情報を含めないでください。
