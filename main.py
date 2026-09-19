#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from collectors.note_collector import NoteCollector
from collectors.hatena_collector import HatenaCollector
from analyzer import ContentAnalyzer
from summarizer import TrendSummarizer
from mailer import EmailSender

handlers = [logging.StreamHandler(sys.stdout)]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)


def validate_config():
    errors = []
    if not config.GMAIL_ADDRESS:
        errors.append("GMAIL_ADDRESS未設定")
    if not config.GMAIL_APP_PASSWORD:
        errors.append("GMAIL_APP_PASSWORD未設定")
    if not config.REPORT_TO_EMAILS:
        errors.append("TO_EMAIL未設定")
    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)


def main():
    validate_config()
    logger.info("=== 週次トレンド収集開始 ===")

    note_collector = NoteCollector()
    note_articles = note_collector.collect()
    logger.info(f"note: {len(note_articles)}件収集")

    hatena_collector = HatenaCollector()
    hatena_entries = hatena_collector.collect()
    logger.info(f"はてブ: {len(hatena_entries)}件収集")

    if not note_articles and not hatena_entries:
        raise RuntimeError("両媒体の取得が0件です。分析・メール送信を中止します。")

    analyzer = ContentAnalyzer()
    note_data = analyzer.analyze_note_articles(note_articles)
    hatena_data = analyzer.analyze_hatena_entries(hatena_entries)

    summarizer = TrendSummarizer()
    trend_summary = summarizer.generate_summary(note_data, hatena_data)

    warnings = note_collector.warnings + hatena_collector.warnings
    if not note_articles:
        warnings.append("noteは0件です。noteの傾向は判断できません。")
    if not hatena_entries:
        warnings.append("はてブは0件です。はてブの傾向は判断できません。")
    if warnings:
        # 外部エラー本文や認証情報は含めず、欠損の種類を必ず利用者に伝える。
        notice = "\n".join(f"- {item}" for item in dict.fromkeys(warnings))
        trend_summary = (
            "## 収集範囲の注意\n" + notice
            + "\n以下は取得できた範囲の分析です。市場全体の傾向ではありません。\n\n"
            + trend_summary
        )

    mailer = EmailSender()
    mailer.send_weekly_report(note_data, hatena_data, trend_summary)

    logger.info("=== 週次トレンド収集完了 ===")


if __name__ == "__main__":
    main()
