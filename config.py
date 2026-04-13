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

# note収集設定
NOTE_TAGS = ["キャリア", "副業", "AI", "プロデューサー", "フリーランス", "コンテンツマーケティング"]
NOTE_ARTICLES_PER_TAG = int(os.getenv("NOTE_ARTICLES_PER_TAG", "10"))

# はてブカテゴリ
HATENA_CATEGORIES = ["business", "economics", "career"]  # ホットエントリRSSカテゴリ
HATENA_ENTRIES_COUNT = int(os.getenv("HATENA_ENTRIES_COUNT", "20"))

# タイトルパターン定義（正規表現）
TITLE_PATTERNS = {
    "数字リスト": r"[０-９0-9]+\s*[つ個本選]|[０-９0-9]+\s*の",
    "疑問形": r"[なぜどうしてなんで].{1,20}[？?]|[か？?]$",
    "ハウツー": r"(方法|やり方|コツ|ポイント|手順|ステップ|やってみ)",
    "体験談": r"(してみた|やってみた|やめた|転職した|辞めた|始めた)",
    "まとめ": r"(まとめ|総まとめ|振り返り|総括)",
    "比較": r"(vs|VS|対|比較|違い|どちら)",
    "警告・逆説": r"(してはいけない|ダメ|注意|失敗|落とし穴|罠|危険)",
    "完全ガイド": r"(完全|徹底|網羅|全解説|保存版)",
}

# HTTPリクエスト共通ヘッダ
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "ja,en-US;q=0.9",
}
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 1.5  # seconds between requests
