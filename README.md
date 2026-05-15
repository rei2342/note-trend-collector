# note-trend-collector

**毎週月曜の朝、noteで売れる記事のネタが自動でメールに届く仕組みです。**

note・はてブのトレンドを自動収集し、Claude AIが「今週書くべきタイトル案」まで分析してGmailに送ります。一度セットアップすれば、あとは完全放置でOKです。

---

## できること

- **note人気記事の自動収集**（いいね順・タイトル型・構成パターン・見出し数を分析）
- **はてブホットエントリの収集**（ビジネス・キャリア・経済系）
- **Claude AIによるトレンドサマリー生成**（今週書くべきタイトル案5本以上）
- **毎週月曜9:00に自動でGmailに送信**（PCの電源を入れる必要なし）

---

## 必要なもの

| 必要なもの | 費用 | 取得場所 |
|---|---|---|
| GitHubアカウント | 無料 | https://github.com |
| Gmailアカウント | 無料 | https://gmail.com |
| Anthropic APIキー | 従量課金（週1回なら月100〜300円程度） | https://console.anthropic.com |

Pythonやターミナルの知識は不要です。GitHubの画面操作だけで完結します。

---

## セットアップ手順（30分で完了）

### ステップ1：このリポジトリをコピーする

1. このページ右上の「Fork」ボタンをクリック
2. 「Create fork」をクリック
3. 自分のGitHubアカウントにコピーされたことを確認

### ステップ2：Gmailのアプリパスワードを取得する

1. https://myaccount.google.com にアクセス
2. 左メニュー「セキュリティ」をクリック
3. 「2段階認証プロセス」をONにする（まだの場合）
4. 検索窓に「アプリパスワード」と入力して開く
5. アプリ名に「note-monitor」と入力して「作成」
6. 表示された**16桁のパスワード**をメモしておく（スペースなしでOK）

### ステップ3：Anthropic APIキーを取得する

1. https://console.anthropic.com にアクセス（Googleアカウントでサインアップ可）
2. 左メニュー「API Keys」→「Create Key」
3. 表示された `sk-ant-...` から始まる文字列をメモしておく

> **費用について：** 週1回の実行なら月100〜300円程度です。初回登録時に$5クレジットが付与されるので、しばらくは実質無料で使えます。

### ステップ4：GitHub Secretsに登録する

1. 自分のGitHubリポジトリページを開く
2. 上部タブ「Settings」をクリック
3. 左メニュー「Secrets and variables」→「Actions」をクリック
4. 「New repository secret」で以下の4つを登録する

| Name（コピーして使う） | Value |
|---|---|
| `GMAIL_ADDRESS` | 送信に使うGmailアドレス |
| `GMAIL_APP_PASSWORD` | ステップ2で取得した16桁 |
| `TO_EMAIL` | 受け取りたいメールアドレス（Gmailと同じでOK） |
| `ANTHROPIC_API_KEY` | ステップ3で取得したAPIキー |

### ステップ5：動作確認する

1. 上部タブ「Actions」をクリック
2. 「Weekly Trend Report」をクリック
3. 右上「Run workflow」→「Run workflow」をクリック
4. 3〜5分後にGmailを確認する

> **注意：** ForkしたリポジトリはデフォルトでActionsが無効になっています。Actionsタブを開いて「I understand my workflows, go ahead and enable them」をクリックしてから実行してください。

メールが届いたら完了です。毎週月曜9:00 JSTに自動で届くようになります。

---

## カスタマイズ

`config.py` を編集することで、収集するジャンルや条件を変更できます。

### 収集するnoteのタグを変更する

```python
NOTE_TAGS = [
    "コンテンツマーケティング",
    "情報発信",
    "note運営",
    # ← ここに追加したいタグを書く
    # 例："ライティング", "ブログ", "Webライター"
]
```

### 複数のメールアドレスに送る

```
# GitHub SecretsのTO_EMAILをカンマ区切りにする
# 例: address1@gmail.com,address2@gmail.com
```

---

## よくある質問

**Q: Pythonをインストールする必要がありますか？**
A: 不要です。すべてGitHubのサーバー上で動きます。

**Q: PCの電源を入れておく必要がありますか？**
A: 不要です。GitHubのクラウド上で動くので、PCがオフでもメールが届きます。

**Q: Claude AIの分析が使えません（ルールベース分析になっている）**
A: ANTHROPIC_API_KEYが正しく設定されているか確認してください。GitHub SecretsのNameに余分なスペースが入っていないかも確認を。

**Q: メールが届きません**
A: Gmailのアプリパスワードが正しいか確認してください。Gmailのパスワード（ログインパスワード）ではなく、ステップ2で生成した**16桁のアプリパスワード**が必要です。

**Q: Actionsが動きません**
A: ForkしたリポジトリはデフォルトでActionsが無効です。Actionsタブを開いて「I understand my workflows, go ahead and enable them」をクリックしてください。

---

## ライセンス

個人利用・商用利用ともに自由に使えます。再販売はご遠慮ください。

---

*質問・不具合報告はGitHub Issuesまでどうぞ。*
