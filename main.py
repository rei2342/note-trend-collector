#!/usr/bin/env python3
"""
note_trend_collector - 週次トレンド収集・分析・メール送信スクリプト
毎週月曜 9:00 にcronで実行する想定。
"""

import os
import sys
import logging
from pathlib import Path

# スクリプトのディレクトリをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent))

import config
from collectors.note_collector import NoteCollector
from collectors.hatena_collector import HatenaCollector
from collectors.x_collector import XCollector
from analyzer import ContentAnalyzer
from summarizer import TrendSummarizer
from mailer import EmailSender

handlers = [logging.StreamHandler(sys.stdout)]
# ローカル実行時のみファイルログを追加
log_file = Path(__file__).parent / "run.log"
if log_file.parent.exists() and not os.getenv("CI"):
    handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)


def validate_config():
    errors = []
    if not config.GMAIL_ADDRESS:
        errors.append("GMAIL_ADDRESS が未設定です")
    if not config.GMAIL_APP_PASSWORD:
        errors.append("GMAIL_APP_PASSWORD が未設定です")
    if not config.REPORT_TO_EMAILS:
        errors.append("TO_EMAIL が未設定です")
    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)


def main():
    validate_config()
    logger.info("=== 週次トレンド収集開始 ===")

    # 1. データ収集
    logger.info("--- note 収集 ---")
    note_articles = NoteCollector().collect()
    logger.info(f"note: {len(note_articles)}件収集")

    logger.info("--- はてブ 収集 ---")
    hatena_entries = HatenaCollector().collect()
    logger.info(f"はてブ: {len(hatena_entries)}件収集")

    logger.info("--- X(Twitter) 収集 ---")
    x_posts = XCollector().collect()
    logger.info(f"X: {len(x_posts)}件収集")

    # 2. 分析
    logger.info("--- 構成分析 ---")
    analyzer = ContentAnalyzer()
    note_data = analyzer.analyze_note_articles(note_articles)
    hatena_data = analyzer.analyze_hatena_entries(hatena_entries)

    # 3. ルールベースサマリー生成
    logger.info("--- ルールベースサマリー生成 ---")
    summarizer = TrendSummarizer()
    trend_summary = summarizer.generate_summary(note_data, hatena_data, x_posts)

    # 4. メール送信
    logger.info("--- メール送信 ---")
    mailer = EmailSender()
    mailer.send_weekly_report(note_data, hatena_data, x_posts, trend_summary)

    logger.info("=== 週次トレンド収集完了 ===")


if __name__ == "__main__":
    main()
