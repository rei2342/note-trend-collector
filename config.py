import os
from dotenv import load_dotenv

load_dotenv()

# Gmail
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
TO_EMAIL = os.getenv("TO_EMAIL", "")
REPORT_TO_EMAILS = [e.strip() for e in os.getenv("TO_EMAIL", os.getenv("REPORT_TO_EMAILS", "")).split(",") if e.strip()]

# X (Twitter)
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
X_MIN_LIKES = int(os.getenv("X_MIN_LIKES", "500"))
X_POSTS_COUNT = int(os.getenv("X_POSTS_COUNT", "20"))

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# note収集設定
NOTE_TAGS = [
    "コンテンツマーケティング",
    "情報発信",
    "note運営",
    "有料note",
    "マネタイズ",
    "副業",
    "キャリア",
    "AI活用",
    "ChatGPT",
    "個人ブランディング",
    "セルフプロデュース",
]
NOTE_ARTICLES_PER_TAG = int(os.getenv("NOTE_ARTICLES_PER_TAG", "15"))

# はてブカテゴリ
HATENA_CATEGORIES = ["business", "economics", "career"]
HATENA_ENTRIES_COUNT = int(os.getenv("HATENA_ENTRIES_COUNT", "20"))

# タイトルパターン定義（正規表現）
TITLE_PATTERNS = {
    "数字リスト": r"[０-９0-9]+\s*[つ個本選]|[０-９0-9]+\s*の",
    "疑問形": r"[なぜどうしてなんで].{1,20}[？?]|[か？?]$",
    "ハウツー": r"(方法|やり方|コツ|ポイント|手順|ステップ|やってみ)",
    "体験談": r"(してみた|やってみた|やめた|転職した|辞めた|始めた)",
    "まとめ": r"(まとめ|総まとめ|振り返り|総括)",
    "比較": r"(vs|VS|対|比較|違い|どちら)",
    "警告・逆説"
