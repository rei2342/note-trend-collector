import time
import logging
import requests
from dataclasses import dataclass
import config

logger = logging.getLogger(__name__)


@dataclass
class XPost:
    tweet_id: str
    text: str
    url: str
    like_count: int
    retweet_count: int
    author_id: str
    author_name: str = ""
    note_url: str = ""  # 含まれるnote.com URL


class XCollector:
    SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
    USERS_URL = "https://api.twitter.com/2/users"

    def __init__(self):
        self.bearer_token = config.X_BEARER_TOKEN
        self.enabled = bool(self.bearer_token)
        if not self.enabled:
            logger.warning("X_BEARER_TOKEN未設定のためX収集をスキップします")

    def collect(self) -> list[XPost]:
        if not self.enabled:
            return []

        logger.info("X(Twitter)収集中...")
        try:
            posts = self._search_note_posts()
            author_ids = list({p.author_id for p in posts if p.author_id})
            name_map = self._fetch_author_names(author_ids)
            for p in posts:
                p.author_name = name_map.get(p.author_id, p.author_id)
            return posts
        except Exception as e:
            logger.warning(f"X収集失敗: {e}")
            return []

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def _search_note_posts(self) -> list[XPost]:
        # note.com URLを含み、リツイートを除外、いいね数フィルタはAPIでは指定不可なので後処理
        query = f"note.com -is:retweet lang:ja"
        params = {
            "query": query,
            "max_results": 100,  # APIの最大値
            "tweet.fields": "public_metrics,author_id,entities",
            "expansions": "author_id",
            "user.fields": "name,username",
        }
        resp = requests.get(
            self.SEARCH_URL,
            headers=self._headers(),
            params=params,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        posts = []
        for tweet in data.get("data", []):
            metrics = tweet.get("public_metrics", {})
            like_count = metrics.get("like_count", 0)

            if like_count < config.X_MIN_LIKES:
                continue

            # note.com URLを抽出
            note_url = ""
            urls = tweet.get("entities", {}).get("urls", [])
            for u in urls:
                expanded = u.get("expanded_url", "")
                if "note.com" in expanded:
                    note_url = expanded
                    break

            tweet_url = f"https://twitter.com/i/web/status/{tweet['id']}"
            posts.append(
                XPost(
                    tweet_id=tweet["id"],
                    text=tweet.get("text", ""),
                    url=tweet_url,
                    like_count=like_count,
                    retweet_count=metrics.get("retweet_count", 0),
                    author_id=tweet.get("author_id", ""),
                    note_url=note_url,
                )
            )
            if len(posts) >= config.X_POSTS_COUNT:
                break

        return sorted(posts, key=lambda p: p.like_count, reverse=True)

    def _fetch_author_names(self, author_ids: list[str]) -> dict[str, str]:
        if not author_ids:
            return {}
        # 一度に100件まで
        ids_str = ",".join(author_ids[:100])
        params = {"ids": ids_str, "user.fields": "name,username"}
        try:
            resp = requests.get(
                self.USERS_URL,
                headers=self._headers(),
                params=params,
                timeout=config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return {
                u["id"]: f"{u['name']} (@{u['username']})"
                for u in resp.json().get("data", [])
            }
        except Exception as e:
            logger.warning(f"ユーザー名取得失敗: {e}")
            return {}
