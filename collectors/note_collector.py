import time
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional
import config

logger = logging.getLogger(__name__)


@dataclass
class NoteArticle:
    title: str
    url: str
    author: str
    tag: str
    like_count: int = 0
    is_paid: bool = False
    body_text: str = ""
    headings: list[str] = field(default_factory=list)
    paid_position: Optional[str] = None
    description: str = ""
    details_fetched: bool = False


class NoteCollector:
    API_BASE = "https://note.com/api/v3"
    ARTICLE_BASE = "https://note.com"

    def __init__(self):
        self.warnings: list[str] = []
        self.session = requests.Session()
        self.session.headers.update(config.REQUEST_HEADERS)

    def collect(self) -> list[NoteArticle]:
        self.warnings = []
        articles: list[NoteArticle] = []
        seen_urls: set[str] = set()

        for tag in config.NOTE_TAGS:
            logger.info(f"note収集中: #{tag}")
            try:
                tag_articles = self._fetch_by_tag(tag)
                logger.info(f"タグ '{tag}': {len(tag_articles)}件取得")
                for a in tag_articles:
                    if a.url not in seen_urls:
                        seen_urls.add(a.url)
                        articles.append(a)
                time.sleep(config.REQUEST_DELAY)
            except Exception as e:
                self.warnings.append(f"noteタグ「{tag}」の取得に失敗しました。")
                logger.warning(f"タグ '{tag}' の収集失敗: {e}")

        top_articles = sorted(articles, key=lambda a: a.like_count, reverse=True)[
            : config.NOTE_ARTICLES_PER_TAG * 2
        ]
        for article in top_articles:
            try:
                self._enrich_article(article)
                time.sleep(config.REQUEST_DELAY)
            except Exception as e:
                self.warnings.append("note記事の公開本文・見出しの取得に失敗しました。")
                logger.warning(f"記事詳細取得失敗 {article.url}: {e}")

        return top_articles

    def _fetch_by_tag(self, tag: str) -> list[NoteArticle]:
        encoded_tag = requests.utils.quote(tag)
        url = f"{self.API_BASE}/hashtags/{encoded_tag}/notes"
        params = {
            "order": "popular",
            "page": 1,
            "paid_only": "false",
        }
        resp = self.session.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        data_obj = data.get("data") or {}
        notes = data_obj.get("notes") or []

        articles = []
        for item in notes:
            user = item.get("user") or {}
            note_url = f"{self.ARTICLE_BASE}/{user.get('urlname', '')}/n/{item.get('key', '')}"
            desc = item.get("body") or ""
            articles.append(
                NoteArticle(
                    title=item.get("name", ""),
                    url=note_url,
                    author=user.get("name", ""),
                    tag=tag,
                    like_count=item.get("like_count", 0),
                    is_paid=item.get("price", 0) > 0,
                    description=desc[:200],
                )
            )
        return articles

    def _enrich_article(self, article: NoteArticle):
        resp = self.session.get(article.url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        article_body = soup.find("div", class_=lambda c: c and "note-common-styles__textnote-body" in c)
        if not article_body:
            article_body = soup.find("div", {"data-testid": "note-body"})
        if not article_body:
            article_body = soup.find("article")

        if article_body is None:
            raise ValueError("公開本文を特定できませんでした")

        if article_body is not None:
            headings = []
            for tag in article_body.find_all(["h1", "h2", "h3", "h4"]):
                text = tag.get_text(strip=True)
                if text:
                    headings.append(f"{tag.name}: {text}")
            article.headings = headings

            # Public HTML does not include the paid body, so its DOM position
            # cannot establish where a paywall falls in the complete article.
            # Keep the dataclass field for compatibility, but do not populate it.
            article.paid_position = None

            if not article.description:
                body_text = article_body.get_text(separator=" ", strip=True)
                article.description = body_text[:200]
            article.details_fetched = True

