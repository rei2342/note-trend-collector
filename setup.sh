#!/bin/bash
# note_trend_collector セットアップスクリプト
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== note_trend_collector セットアップ ==="

# Python バージョン確認
python3 --version || { echo "ERROR: python3が見つかりません"; exit 1; }

# 仮想環境作成
if [ ! -d ".venv" ]; then
    echo "[1/4] 仮想環境を作成中..."
    python3 -m venv .venv
else
    echo "[1/4] 仮想環境は既に存在します"
fi

# 依存パッケージインストール
echo "[2/4] パッケージをインストール中..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
echo "      インストール完了"

# .env ファイル作成
if [ ! -f ".env" ]; then
    echo "[3/4] .env ファイルを作成中..."
    cp .env.example .env
    echo "      .env を作成しました。編集して必要な値を設定してください:"
    echo "      - ANTHROPIC_API_KEY"
    echo "      - GMAIL_ADDRESS / GMAIL_APP_PASSWORD"
    echo "      - REPORT_TO_EMAILS"
    echo "      （任意）X_BEARER_TOKEN"
else
    echo "[3/4] .env ファイルは既に存在します"
fi

# cron 設定
echo ""
echo "[4/4] cron設定"
echo "  以下のコマンドで crontab を編集し、毎週月曜9:00に実行を設定してください:"
echo ""
echo "  crontab -e"
echo ""
echo "  追加する行:"
echo "  0 9 * * 1 $SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/main.py >> $SCRIPT_DIR/cron.log 2>&1"
echo ""

# cron自動追加の確認
read -p "  cronに自動追加しますか？ [y/N]: " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    CRON_LINE="0 9 * * 1 $SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/main.py >> $SCRIPT_DIR/cron.log 2>&1"
    # 既存のcronに追加（重複チェックあり）
    if crontab -l 2>/dev/null | grep -qF "$SCRIPT_DIR/main.py"; then
        echo "  既にcronに登録済みです"
    else
        (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
        echo "  cronに追加しました"
    fi
fi

echo ""
echo "=== セットアップ完了 ==="
echo "  動作確認: .venv/bin/python main.py"
