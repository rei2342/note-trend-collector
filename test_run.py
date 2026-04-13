#!/usr/bin/env python3
"""
各モジュールの動作確認スクリプト。
本番実行前にメール送信なしでテストするために使用。

使い方:
  python test_run.py             # 全モジュールをテスト
  python test_run.py note        # noteのみ
  python test_run.py hatena      # はてブのみ
  python test_run.py x           # Xのみ
  python test_run.py analyze     # 分析のみ（フィクスチャデータ使用）
  python test_run.py summary     # Claudeサマリー生成のみ（フィクスチャ使用）
  python test_run.py mail        # メール送信のみ（フィクスチャ使用）
"""

import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

import config
from collectors.note_collector import NoteCollector, NoteArticle
from collectors.hatena_collector import HatenaCollector, HatenaEntry
from collectors.x_collector import XCollector, XPost
from analyzer import ContentAnalyzer
from summarizer import TrendSummarizer
from mailer import EmailSender


def make_fixture_note() -> list[NoteArticle]:
    """テスト用フィクスチャ（note記事）"""
    return [
        NoteArticle(
            title="AIを使って副業収入を3倍にした5つの方法",
            url="https://note.com/example/n/abc123",
            author="テストユーザー",
            tag="AI",
            like_count=1200,
            is_paid=True,
            description="AIツールを活用して副業収入を増やした実体験をまとめました。",
            headings=["h2: はじめに", "h2: 方法1：ChatGPTで記事量産", "h3: 実際の収益", "h2: まとめ"],
            paid_position="middle",
        ),
        NoteArticle(
            title="なぜ転職に失敗する人が多いのか？原因と対策を徹底解説",
            url="https://note.com/example/n/def456",
            author="キャリアコーチ",
            tag="キャリア",
            like_count=850,
            is_paid=False,
            description="転職活動でよくある失敗パターンを分析し、成功するための具体的な方法を解説します。",
            headings=["h2: 転職失敗の3大原因", "h3: 自己分析不足", "h3: 市場理解不足", "h2: 対策"],
        ),
        NoteArticle(
            title="フリーランスプロデューサーとして独立してみた【完全ガイド】",
            url="https://note.com/example/n/ghi789",
            author="フリープロデューサー",
            tag="プロデューサー",
            like_count=620,
            is_paid=True,
            description="会社員からフリーランスプロデューサーへ転身した全記録。",
            headings=["h2: 独立前の準備", "h2: 最初の3ヶ月", "h2: 収入の安定化"],
            paid_position="late",
        ),
    ]


def make_fixture_hatena() -> list[HatenaEntry]:
    return [
        HatenaEntry(
            title="年収1000万円を超えたエンジニアが実践していること10選",
            url="https://example.com/article1",
            description="高年収エンジニアの共通点を調査しました。",
            bookmark_count=450,
            category="business",
        ),
        HatenaEntry(
            title="副業解禁後に陥りがちな罠と回避策",
            url="https://example.com/article2",
            description="副業を始めた人が最初にやりがちなミスをまとめました。",
            bookmark_count=320,
            category="career",
        ),
    ]


def make_fixture_x() -> list[XPost]:
    return [
        XPost(
            tweet_id="123456789",
            text="noteに記事を書いたらバズった話。キャリア系の記事は夜9時〜11時に投稿すると伸びやすい。note.com/example/n/abc123",
            url="https://twitter.com/i/web/status/123456789",
            like_count=1500,
            retweet_count=300,
            author_id="user1",
            author_name="バズるライター (@buzzer)",
            note_url="https://note.com/example/n/abc123",
        ),
    ]


def test_note():
    logger.info("=== note収集テスト ===")
    articles = NoteCollector().collect()
    logger.info(f"収集件数: {len(articles)}")
    for a in articles[:3]:
        logger.info(f"  [{a.tag}] {a.title} (いいね:{a.like_count}, 有料:{a.is_paid})")
        if a.headings:
            logger.info(f"    見出し: {a.headings[:3]}")
    return articles


def test_hatena():
    logger.info("=== はてブ収集テスト ===")
    entries = HatenaCollector().collect()
    logger.info(f"収集件数: {len(entries)}")
    for e in entries[:3]:
        logger.info(f"  {e.title} (ブクマ:{e.bookmark_count})")
    return entries


def test_x():
    logger.info("=== X収集テスト ===")
    posts = XCollector().collect()
    logger.info(f"収集件数: {len(posts)}")
    for p in posts[:3]:
        logger.info(f"  いいね:{p.like_count} / {p.text[:60]}...")
    return posts


def test_analyze(note_articles=None, hatena_entries=None):
    logger.info("=== 分析テスト ===")
    if note_articles is None:
        note_articles = make_fixture_note()
    if hatena_entries is None:
        hatena_entries = make_fixture_hatena()

    analyzer = ContentAnalyzer()
    note_data = analyzer.analyze_note_articles(note_articles)
    hatena_data = analyzer.analyze_hatena_entries(hatena_entries)

    analyzed_notes, note_stats = note_data
    logger.info(f"noteタイトルパターン: {note_stats.title_pattern_counts}")
    logger.info(f"有料化位置: {note_stats.paid_position_counts}")
    logger.info(f"平均見出し数: {note_stats.avg_heading_count}")
    for a in analyzed_notes:
        logger.info(f"  [{a.title_pattern}] {a.title[:40]} / {a.structure_summary}")

    return note_data, hatena_data


def test_summary(note_data=None, hatena_data=None, x_posts=None):
    logger.info("=== ルールベースサマリー生成テスト ===")
    if note_data is None:
        analyzer = ContentAnalyzer()
        note_data = analyzer.analyze_note_articles(make_fixture_note())
        hatena_data = analyzer.analyze_hatena_entries(make_fixture_hatena())
    if x_posts is None:
        x_posts = make_fixture_x()

    summary = TrendSummarizer().generate_summary(note_data, hatena_data, x_posts)
    logger.info("生成されたサマリー（抜粋）:")
    logger.info(summary[:500])
    return summary


def test_mail(note_data=None, hatena_data=None, x_posts=None, summary=None):
    logger.info("=== メール送信テスト ===")
    if not all([config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD, config.REPORT_TO_EMAILS]):
        logger.warning("Gmail設定が不完全のためスキップ")
        return
    if note_data is None:
        analyzer = ContentAnalyzer()
        note_data = analyzer.analyze_note_articles(make_fixture_note())
        hatena_data = analyzer.analyze_hatena_entries(make_fixture_hatena())
    if x_posts is None:
        x_posts = make_fixture_x()
    if summary is None:
        summary = "## 今週のトレンドサマリー\n\nテスト送信のためダミーサマリーです。"

    EmailSender().send_weekly_report(note_data, hatena_data, x_posts, summary)
    logger.info("メール送信テスト完了")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "note":
        test_note()
    elif mode == "hatena":
        test_hatena()
    elif mode == "x":
        test_x()
    elif mode == "analyze":
        test_analyze()
    elif mode == "summary":
        test_summary()
    elif mode == "mail":
        test_mail()
    elif mode == "all":
        # フィクスチャで全パイプラインテスト（実際のAPI呼び出しは環境次第）
        logger.info("フィクスチャデータで全パイプラインをテストします")
        note_data, hatena_data = test_analyze()
        summary = test_summary(note_data, hatena_data, make_fixture_x())
        test_mail(note_data, hatena_data, make_fixture_x(), summary)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
