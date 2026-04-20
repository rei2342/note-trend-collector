"""
Claude APIを使ったトレンドサマリー生成
収集・分析データをClaudeに渡し、note売上最大化の視点で深く分析する。
"""

import logging
import os
import json
import urllib.request
import urllib.error
from collections import Counter
from collectors.x_collector import XPost
from analyzer import AnalyzedNote, AnalyzedHatena, PatternStats
import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはnoteで売れるコンテンツを作るための戦略アドバイザーです。
毎週月曜日に、note・はてブ・Xのトレンドデータを分析し、「今週どんなnoteを書けば売れるか」を導き出すのが仕事です。

分析視点：
- どのタイトルパターン・テーマが今週バズっているか
- 有料記事の設計（有料化位置・価格設定・見出し構成）で成功しているパターン
- 読者が今週「何に悩み・何を求めているか」の本質的なニーズ
- はてブ・Xのバズから、noteで先取りできるテーマ
- 具体的に「今週書くべきnoteのタイトル案」を複数提示

出力形式：Markdown（日本語）
読む人は一人のnoteクリエイターで、売れるコンテンツを作りたいという強い意志がある。
分析は深く、具体的に。抽象論ではなく「明日使えるインサイト」を出す。"""


def _call_claude_api(prompt: str) -> str:
    api_key = config.ANTHROPIC_API_KEY
    logger.info(f"ANTHROPIC_API_KEY設定状況: {'あり' if api_key else 'なし'}")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY未設定のためルールベースサマリーにフォールバック")
        return ""

    payload = json.dumps({
        "model": "claude-opus-4-5",
        "max_tokens": 2000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        logger.error(f"Claude API HTTPError {e.code}: {body}")
        return ""
    except Exception as e:
        logger.error(f"Claude API呼び出し失敗: {e}")
        return ""


def _build_analysis_prompt(
    note_articles: list[AnalyzedNote],
    note_stats: PatternStats,
    hatena_entries: list[AnalyzedHatena],
    hatena_stats: PatternStats,
    x_posts: list[XPost],
) -> str:
    lines = ["# 今週のトレンドデータ（分析してください）", ""]

    lines.append("## note人気記事（いいね順）")
    lines.append(f"収集件数: {len(note_articles)}件")
    lines.append("")
    for a in note_articles[:20]:
        paid_str = f"【有料・{a.paid_position or '不明'}配置】" if a.is_paid else "【無料】"
        heading_str = f"見出し{a.heading_count}個" if a.heading_count else "見出しなし"
        lines.append(f"- いいね{a.like_count} {paid_str} タイトル型:{a.title_pattern} {heading_str}")
        lines.append(f"  タイトル: {a.title}")
        if a.description:
            lines.append(f"  概要: {a.description[:150]}")
        if a.headings:
            lines.append(f"  主な見出し: {' / '.join(h.split(': ',1)[-1] for h in a.headings[:5])}")
        lines.append("")

    lines.append("## note統計サマリー")
    lines.append(f"タイトルパターン分布: {json.dumps(note_stats.title_pattern_counts, ensure_ascii=False)}")
    lines.append(f"有料化位置分布: {json.dumps(note_stats.paid_position_counts, ensure_ascii=False)}")
    lines.append(f"平均見出し数: {note_stats.avg_heading_count}個")
    lines.append(f"上位タグ: {', '.join(note_stats.top_tags)}")
    lines.append("")

    lines.append("## はてブホットエントリ（ビジネス・キャリア系）")
    for e in hatena_entries[:10]:
        lines.append(f"- ブクマ{e.bookmark_count} タイトル型:{e.title_pattern}")
        lines.append(f"  タイトル: {e.title}")
        if e.description:
            lines.append(f"  概要: {e.description[:100]}")
        lines.append("")

    if x_posts:
        lines.append("## Xバズ投稿（note関連・いいね順）")
        for p in x_posts[:10]:
            lines.append(f"- いいね{p.like_count} RT{p.retweet_count} @{p.author_name}")
            lines.append(f"  {p.text[:150]}")
            if p.note_url:
                lines.append(f"  note: {p.note_url}")
            lines.append("")
    else:
        lines.append("## X: データなし（Bearer Token未設定）")
        lines.append("")

    lines.append("---")
    lines.append("上記データをもとに、以下の構成でレポートを作成してください：")
    lines.append("")
    lines.append("### 1. 今週の読者ニーズ分析")
    lines.append("（読者が今週何を求めているか、データから読み取れる本質的なニーズ）")
    lines.append("")
    lines.append("### 2. 売れているnoteの共通パターン")
    lines.append("（タイトル・構成・有料設計・テーマの勝ちパターンを具体的に）")
    lines.append("")
    lines.append("### 3. はてブ・Xから先取りできるテーマ")
    lines.append("（まだnoteで書かれていないが、今週バズっている話題からnote化できるネタ）")
    lines.append("")
    lines.append("### 4. 今週書くべきnoteタイトル案（5本以上）")
    lines.append("（具体的なタイトル文字列で。タイトルパターン・想定いいね数・有料or無料の推奨も添える）")
    lines.append("")
    lines.append("### 5. 今週の一言インサイト")
    lines.append("（一番重要なポイントを1〜2文で）")

    return "\n".join(lines)


def _fallback_summary(
    note_articles: list[AnalyzedNote],
    note_stats: PatternStats,
    hatena_entries: list[AnalyzedHatena],
    hatena_stats: PatternStats,
    x_posts: list[XPost],
) -> str:
    top_tag = note_stats.top_tags[0] if note_stats.top_tags else "キャリア"
    top_pattern = max(note_stats.title_pattern_counts, key=note_stats.title_pattern_counts.get) if note_stats.title_pattern_counts else "その他"

    sections = []

    theme_lines = ["## 今週のトレンドサマリー", "", "### 1. 今週のキーテーマ"]
    THEME_KEYWORDS = {
        "AI活用": ["AI", "ChatGPT", "Claude", "生成AI", "自動化"],
        "キャリア転換": ["転職", "独立", "フリーランス", "起業", "副業"],
        "収益化": ["収益", "マネタイズ", "有料", "稼ぐ", "収入"],
        "スキルアップ": ["スキル", "勉強", "学習", "資格"],
        "マーケティング": ["マーケティング", "集客", "SNS", "フォロワー"],
    }
    all_text = " ".join([a.title + " " + a.description for a in note_articles] + [e.title + " " + e.description for e in hatena_entries])
    for theme, keywords in THEME_KEYWORDS.items():
        hit_kw = [kw for kw in keywords if kw in all_text]
        if hit_kw:
            theme_lines.append(f"- **{theme}** — 「{'・'.join(hit_kw[:3])}」関連の記事が複数登場")
    sections.append("\n".join(theme_lines))

    pattern_lines = ["### 2. 勝ちパターン分析"]
    if note_stats.title_pattern_counts:
        top_name, top_cnt = sorted(note_stats.title_pattern_counts.items(), key=lambda x: -x[1])[0]
        pattern_lines.append(f"- **タイトルの型**: 「{top_name}」が最多（{top_cnt}件）")
    avg = note_stats.avg_heading_count
    pattern_lines.append(f"- **見出し構成**: 平均{avg}個")
    sections.append("\n".join(pattern_lines))

    pickup_lines = ["### 3. 今週注目の記事"]
    for a in sorted(note_articles, key=lambda a: a.like_count, reverse=True)[:3]:
        pickup_lines.append(f"- **[note]** [{a.title}]({a.url})（いいね {a.like_count}）")
    if hatena_entries:
        top_h = max(hatena_entries, key=lambda e: e.bookmark_count)
        pickup_lines.append(f"- **[はてブ]** [{top_h.title}]({top_h.url})（ブクマ {top_h.bookmark_count}）")
    sections.append("\n".join(pickup_lines))

    sections.append(f"### 4. 一言まとめ\n「**{top_tag}**」テーマ × 「**{top_pattern}**」型タイトルの組み合わせが今週の主役。")

    return "\n\n".join(sections)


class TrendSummarizer:
    def generate_summary(
        self,
        note_data: tuple[list[AnalyzedNote], PatternStats],
        hatena_data: tuple[list[AnalyzedHatena], PatternStats],
        x_posts: list[XPost],
    ) -> str:
        note_articles, note_stats = note_data
        hatena_entries, hatena_stats = hatena_data

        import os
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        logger.info(f"ANTHROPIC_API_KEY直接取得: {'あり' if api_key else 'なし'}")

        if api_key:
            logger.info("Claude APIでサマリー生成中...")
            prompt = _build_analysis_prompt(note_articles, note_stats, hatena_entries, hatena_stats, x_posts)
            # 一時的にapi_keyを直接渡す
            payload = json.dumps({
                "model": "claude-opus-4-5",
                "max_tokens": 2000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    result = data["content"][0]["text"]
                    logger.info("Claude APIサマリー生成完了")
                    return "## 今週のトレンドサマリー（AI分析）\n\n" + result
            except Exception as e:
                logger.error(f"Claude API失敗: {e}")

        return _fallback_summary(note_articles, note_stats, hatena_entries, hatena_stats, x_posts)
