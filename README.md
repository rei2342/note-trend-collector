# note_trend_collector

note・はてブ・X の人気コンテンツを毎週月曜に自動収集し、構成分析とAIサマリーをメールで送るシステム。

## ディレクトリ構成

```
note_trend_collector/
├── main.py               # メインエントリポイント
├── config.py             # 設定読み込み
├── analyzer.py           # タイトル・構成パターン分析
├── summarizer.py         # Claude APIによるトレンドサマリー生成
├── mailer.py             # HTMLメール生成・送信
├── test_run.py           # 動作確認スクリプト
├── setup.sh              # セットアップ・cron登録スクリプト
├── requirements.txt      # 依存パッケージ
├── .env.example          # 環境変数テンプレート
└── collectors/
    ├── note_collector.py     # note API + スクレイピング
    ├── hatena_collector.py   # はてブRSS + ブックマーク数取得
    └── x_collector.py        # X(Twitter) API v2
```

## セットアップ

```bash
cd note_trend_collector
bash setup.sh
```

セットアップスクリプトが以下を行います：
1. Python仮想環境 `.venv` 作成
2. 依存パッケージインストール
3. `.env` ファイル作成（.env.example からコピー）
4. cron設定のガイド（自動追加も可能）

## 環境変数設定

`.env` を編集して値を設定：

```env
ANTHROPIC_API_KEY=sk-ant-...     # 必須
GMAIL_ADDRESS=you@gmail.com      # 必須
GMAIL_APP_PASSWORD=xxxx xxxx ... # 必須（Googleアプリパスワード）
REPORT_TO_EMAILS=to@example.com  # 必須（カンマ区切りで複数可）
X_BEARER_TOKEN=AAAA...           # 任意（未設定時はXをスキップ）
```

### Gmailアプリパスワードの取得方法
1. Googleアカウント → セキュリティ → 2段階認証を有効化
2. セキュリティ → アプリパスワード → アプリを選択「メール」、デバイス「その他」
3. 生成された16文字のパスワードを `GMAIL_APP_PASSWORD` に設定

### X API Bearer Tokenの取得方法
1. https://developer.twitter.com でアプリ作成
2. 「Keys and Tokens」→「Bearer Token」をコピー

## 動作確認

```bash
# 全パイプラインをフィクスチャデータで確認
.venv/bin/python test_run.py

# 各モジュール単体テスト
.venv/bin/python test_run.py note     # note API疎通確認
.venv/bin/python test_run.py hatena   # はてブRSS確認
.venv/bin/python test_run.py x        # X API確認
.venv/bin/python test_run.py summary  # Claude API確認
.venv/bin/python test_run.py mail     # メール送信確認
```

## 手動実行

```bash
.venv/bin/python main.py
```

## cron設定（毎週月曜 9:00）

```bash
crontab -e
```

以下を追加：

```
0 9 * * 1 /path/to/note_trend_collector/.venv/bin/python /path/to/note_trend_collector/main.py >> /path/to/note_trend_collector/cron.log 2>&1
```

## 収集・分析内容

| 項目 | 内容 |
|------|------|
| note | キャリア・副業・AI・プロデューサー等のタグで人気記事を収集。見出し構造・有料化位置を抽出 |
| はてブ | ビジネス・キャリア系ホットエントリをRSSで収集。キーワードフィルタ後にブックマーク数取得 |
| X | note.comURLを含むいいね500以上の投稿を収集（X API v2が必要） |
| 分析 | タイトルの型（数字リスト・疑問形・ハウツー等）、有料化位置（序盤/中盤/終盤）、見出し構成を分類 |
| サマリー | Claude Opus 4.6 でトレンドキーワード・勝ちパターン・来週のネタ提案を生成 |

## タイトルパターン分類

- **数字リスト**: 「5つの方法」「3選」など
- **疑問形**: 「なぜ〜？」「どうすれば〜？」
- **ハウツー**: 「方法・コツ・やり方・ステップ」
- **体験談**: 「〜してみた・やめた・始めた」
- **まとめ**: 「まとめ・振り返り・総括」
- **比較**: 「vs・どちら・違い」
- **警告・逆説**: 「してはいけない・失敗・罠」
- **完全ガイド**: 「完全・徹底・保存版」
