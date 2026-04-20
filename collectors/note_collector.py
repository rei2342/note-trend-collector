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


class NoteCollector:
    API_BASE = "https://note.com/api/v2"
    ARTICLE_BASE = "https://note.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(config.REQUEST_HEADERS)

    def collect(self) -> list[NoteArticle]:
        articles: list[NoteArticle] = []
        seen_urls: set[str] = set()

        for tag in config.NOTE_TAGS:
            logger.info(f"note収集中: #{tag}")
            try:
                tag_articles = self._fetch_by_tag(tag)
                for a in tag_articles:
                    if a.url not in seen_urls:
                        seen_urls.add(a.url)
                        articles.append(a)
                time.sleep(config.REQUEST_DELAY)
            except Exception as e:
                logger.warning(f"タグ '{tag}' の収集失敗: {e}")

        top_articles = sorted(articles, key=lambda a: a.like_count, reverse=True)[
            : config.NOTE_ARTICLES_PER_TAG * 2
        ]
        for article in top_articles:
            try:
                self._enrich_article(article)
                time.sleep(config.REQUEST_DELAY)
            except Exception as e:
                logger.warning(f"記事詳細取得失敗 {article.url}: {e}")

        return top_articles

    def _fetch_by_tag(self, tag: str) -> list[NoteArticle]:
        encoded_tag = requests.utils.quote(tag)
        url = f"{self.API_BASE}/tags/{encoded_tag}/notes"
        params = {
            "size": config.NOTE_ARTICLES_PER_TAG,
            "page": 1,
            "sort": "like",
        }
        try:
            resp = self.session.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # フォールバック: 検索APIを試す
            url2 = f"{self.API_BASE}/searches"
            params2 = {
                "context": "note",
                "q": tag,
                "size": config.NOTE_ARTICLES_PER_TAG,
                "page": 1,
                "sort": "like",
            }
            resp = self.session.get(url2, params=params2, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

        articles = []
        notes = data.get("data", {}).get("notes", [])
        for item in notes:
            note_url = f"{self.ARTICLE_BASE}/{item.get('user', {}).get('urlname', '')}/n/{item.get('key', '')}"
            articles.append(
                NoteArticle(
                    title=item.get("name", ""),
                    url=note_url,
                    author=item.get("user", {}).get("name", ""),
                    tag=tag,
                    like_count=item.get("likeCount", 0),
                    is_paid=item.get("price", 0) > 0,
                    description=item.get("description", "")[:200],
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

        if article_body:
            headings = []
            for tag in article_body.find_all(["h1", "h2", "h3", "h4"]):
                text = tag.get_text(strip=True)
                if text:
                    headings.append(f"{tag.name}: {text}")
            article.headings = headings[:15]

            paid_block = article_body.find(
                lambda t: t.name and t.get_text(strip=True) in ["続きをみるには", "この続きをみるには", "有料記事"]
            )
            if not paid_block:
                paid_block = soup.find("div", class_=lambda c: c and "paid" in str(c).lower())

            if paid_block:
                paid_idx = None
                for i, child in enumerate(article_body.descendants):
                    if child == paid_block:
                        paid_idx = i
                        break
                total = sum(1 for _ in article_body.descendants)
                if paid_idx is not None and total > 0:
                    ratio = paid_idx / total
                    if ratio < 0.35:
                        article.paid_position = "early"
                    elif ratio < 0.65:
                        article.paid_position = "middle"
                    else:
                        article.paid_position = "late"

            if not article.description:
                body_text = article_body.get_text(separator=" ", strip=True)
                article.description = body_text[:200]
