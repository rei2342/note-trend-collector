import time
import logging
import requests
import feedparser
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import config

logger = logging.getLogger(__name__)


@dataclass
class HatenaEntry:
    title: str
    url: str
    description: str
    bookmark_count: int | None = None
    category: str = ""
    tags: list[str] = field(default_factory=list)


class HatenaCollector:
    RSS_BASE = "https://b.hatena.ne.jp/hotentry/{category}.rss"
    # ビジネス・キャリア系カテゴリとRSSカテゴリのマッピング
    CATEGORY_MAP = {
        "business": "economics",   # はてブRSSカテゴリ
        "career": "general",
        "life": "life",
    }
    # キャリア・ビジネス関連キーワードフィルタ
    KEYWORDS = [
        "キャリア", "転職", "副業", "仕事", "ビジネス", "マネジメント", "起業",
        "フリーランス", "スキル", "マーケティング", "AI", "DX", "生産性",
        "プロデューサー", "コンテンツ", "収益", "monetize", "career",
    ]

    def __init__(self):
        self.warnings: list[str] = []
        self.session = requests.Session()
        self.session.headers.update(config.REQUEST_HEADERS)

    def collect(self) -> list[HatenaEntry]:
        self.warnings = []
        entries: list[HatenaEntry] = []
        seen_urls: set[str] = set()
        seen_categories: set[str] = set()

        for category in config.HATENA_CATEGORIES:
            canonical = self.CATEGORY_MAP.get(category, category)
            if canonical in seen_categories:
                continue
            seen_categories.add(canonical)
            logger.info(f"はてブ収集中: {category}")
            try:
                rss_entries = self._fetch_rss(category)
                for e in rss_entries:
                    if e.url not in seen_urls:
                        seen_urls.add(e.url)
                        entries.append(e)
                time.sleep(config.REQUEST_DELAY)
            except Exception as ex:
                self.warnings.append(f"はてブカテゴリ「{category}」の取得に失敗しました。")
                logger.warning(f"はてブ '{category}' の収集失敗: {ex}")

        # キャリア・ビジネス系フィルタ
        filtered = [e for e in entries if self._is_relevant(e)]

        # ブックマーク数取得（Hatena Entry API）
        # 件数は処理予算。未取得の記事まで人気順に並べたように見せない。
        candidates = filtered[: config.HATENA_ENTRIES_COUNT]
        for entry in candidates:
            try:
                self._enrich_bookmark_count(entry)
                time.sleep(0.5)
            except Exception as ex:
                self.warnings.append("はてブ記事のブックマーク数を取得できませんでした。")
                logger.warning(f"ブックマーク数取得失敗 {entry.url}: {ex}")

        return sorted(candidates, key=lambda e: e.bookmark_count if e.bookmark_count is not None else -1, reverse=True)

    def _fetch_rss(self, category: str) -> list[HatenaEntry]:
        rss_category = self.CATEGORY_MAP.get(category, category)
        url = self.RSS_BASE.format(category=rss_category)
        response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            raise ValueError("RSS形式の解析に失敗しました")

        entries = []
        for item in feed.entries:
            desc = BeautifulSoup(item.get("summary", ""), "lxml").get_text(strip=True)
            tags = [t.get("term", "") for t in item.get("tags", [])]
            entries.append(
                HatenaEntry(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    description=desc[:200],
                    category=category,
                    tags=tags,
                )
            )
        return entries

    def _is_relevant(self, entry: HatenaEntry) -> bool:
        text = (entry.title + " " + entry.description).lower()
        return any(kw.lower() in text for kw in self.KEYWORDS)

    def _enrich_bookmark_count(self, entry: HatenaEntry):
        api_url = "https://bookmark.hatenaapis.com/count/entry"
        resp = self.session.get(
            api_url, params={"url": entry.url}, timeout=config.REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        count = int(resp.text.strip())
        if count < 0:
            raise ValueError("ブックマーク数が負数です")
        entry.bookmark_count = count
