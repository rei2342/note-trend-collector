import smtplib
import logging
import ssl
from html import escape, unescape
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from analyzer import AnalyzedNote, AnalyzedHatena, PatternStats
import config

logger = logging.getLogger(__name__)

PAID_POS_LABEL = {"early": "序盤（HTML構造による推定）", "middle": "中盤（HTML構造による推定）", "late": "終盤（HTML構造による推定）"}


def _md_to_html_basic(text: str) -> str:
    import re
    lines = escape(text).split("\n")
    html_lines = []
    in_list = False
    for line in lines:
        is_item = line.startswith(("- ", "* "))
        if in_list and not is_item:
            html_lines.append("</ul>")
            in_list = False
        if is_item and not in_list:
            html_lines.append("<ul>")
            in_list = True
        if line.startswith("### "):
            html_lines.append(f"<h3 style='color:#333;margin-top:20px'>{line[4:]}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2 style='color:#1a1a1a;border-bottom:2px solid #41b883;padding-bottom:6px'>{line[3:]}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1 style='color:#1a1a1a'>{line[2:]}</h1>")
        elif line.startswith("- "):
            html_lines.append(f"<li style='margin:4px 0'>{line[2:]}</li>")
        elif line.startswith("* "):
            html_lines.append(f"<li style='margin:4px 0'>{line[2:]}</li>")
        else:
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            line = re.sub(r"`(.+?)`", r"<code style='background:#f0f0f0;padding:2px 4px'>\1</code>", line)
            html_lines.append(f"<p style='margin:6px 0'>{line}</p>" if line.strip() else "<br>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def _safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
            return "#"
        if any(ord(c) < 32 or c.isspace() for c in value):
            return "#"
        return escape(value, quote=True)
    except ValueError:
        return "#"


class EmailSender:
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587

    def send_weekly_report(
        self,
        note_data: tuple[list[AnalyzedNote], PatternStats],
        hatena_data: tuple[list[AnalyzedHatena], PatternStats],
        trend_summary: str,
    ):
        if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
            raise ValueError("GMAIL_ADDRESS または GMAIL_APP_PASSWORD が未設定です")
        if not config.REPORT_TO_EMAILS:
            raise ValueError("REPORT_TO_EMAILS が未設定です")

        html_body = self._build_html(note_data, hatena_data, trend_summary)
        date_str = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d")
        subject = f"【週次トレンドレポート】{date_str} note・はてブ 収集記事まとめ"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.GMAIL_ADDRESS
        msg["To"] = ", ".join(config.REPORT_TO_EMAILS)
        msg.attach(MIMEText(self._build_plain(note_data, hatena_data, trend_summary), "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            server.sendmail(
                config.GMAIL_ADDRESS,
                config.REPORT_TO_EMAILS,
                msg.as_string(),
            )
        logger.info("メール送信完了（%d宛先）", len(config.REPORT_TO_EMAILS))

    def _build_plain(self, note_data, hatena_data, trend_summary) -> str:
        notes, stats = note_data
        entries, _ = hatena_data
        lines = [trend_summary, "", "出典・収集範囲",
                 "指定タグ・RSSと取得上限内の候補です。市場全体の順位・売上・今週の伸びを示すものではありません。",
                 f"note：集計 {len(notes)}件 ／ 掲載 {min(len(notes), 20)}件",
                 f"公開本文取得済み {stats.heading_sample_count}件。未取得は見出し数の平均から除外します。"]
        for idx, article in enumerate(notes[:20], 1):
            url = _safe_url(article.url)
            lines.extend([f"・[N{idx}] {article.title} ／ #{article.tag} ／ いいね {article.like_count}",
                          unescape(url) if url != "#" else "（安全な出典URLを取得できませんでした）"])
        lines.extend(["", f"はてブ：集計 {len(entries)}件 ／ 掲載 {min(len(entries), 15)}件"])
        for idx, entry in enumerate(entries[:15], 1):
            url = _safe_url(entry.url)
            count = entry.bookmark_count if entry.bookmark_count is not None else "未取得"
            lines.extend([f"・[H{idx}] {entry.title} ／ ブックマーク {count}",
                          unescape(url) if url != "#" else "（安全な出典URLを取得できませんでした）"])
        return "\n".join(lines)

    def _build_html(
        self,
        note_data: tuple[list[AnalyzedNote], PatternStats],
        hatena_data: tuple[list[AnalyzedHatena], PatternStats],
        trend_summary: str,
    ) -> str:
        note_articles, note_stats = note_data
        hatena_entries, hatena_stats = hatena_data
        date_str = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y年%m月%d日")

        # note記事HTML
        note_rows = ""
        for idx, a in enumerate(note_articles[:20], 1):
            paid_badge = (
                f"<span style='background:#e74c3c;color:#fff;padding:2px 6px;border-radius:3px;font-size:11px'>有料</span> "
                if a.is_paid else ""
            )
            paid_pos_str = PAID_POS_LABEL.get(a.paid_position or "", "") if a.paid_position else ""
            headings_str = "<br>".join(escape(h) for h in a.headings[:5]) if a.headings else "（見出し情報なし）"
            heading_label = (
                f"{a.heading_count}個" + (f" (h{a.heading_depth}まで)" if a.heading_depth else "")
                if a.details_fetched else "未取得"
            )
            note_rows += f"""
            <tr style='border-bottom:1px solid #eee'>
              <td style='padding:10px;vertical-align:top'>
                [N{idx}] {paid_badge}<a href="{_safe_url(a.url)}" style='color:#41b883;text-decoration:none;font-weight:bold'>{escape(str(a.title))}</a>
                <br><small style='color:#888'>@{escape(str(a.author))} ／ #{escape(str(a.tag))} ／ いいね {a.like_count}</small>
                <br><small style='color:#666'>{escape(str(a.description[:120]))}...</small>
              </td>
              <td style='padding:10px;vertical-align:top;font-size:12px;color:#555;min-width:160px'>
                <strong>型:</strong> {escape(str(a.title_pattern))}<br>
                <strong>公開部分の見出し:</strong> {heading_label}<br>
                {f'<strong>有料化:</strong> {paid_pos_str}' if paid_pos_str else ''}
              </td>
              <td style='padding:10px;vertical-align:top;font-size:11px;color:#777;max-width:200px'>
                {headings_str}
              </td>
            </tr>"""

        # はてブHTML
        hatena_rows = ""
        for idx, e in enumerate(hatena_entries[:15], 1):
            hatena_rows += f"""
            <tr style='border-bottom:1px solid #eee'>
              <td style='padding:10px'>
                [H{idx}] <a href="{_safe_url(e.url)}" style='color:#0078d4;text-decoration:none;font-weight:bold'>{escape(str(e.title))}</a>
                <br><small style='color:#888'>ブックマーク {e.bookmark_count if e.bookmark_count is not None else '未取得'} ／ {escape(str(e.category))}</small>
                <br><small style='color:#666'>{escape(str(e.description[:100]))}...</small>
              </td>
              <td style='padding:10px;font-size:12px;color:#555'>
                <strong>型:</strong> {escape(str(e.title_pattern))}
              </td>
            </tr>"""

        def pattern_bars(counts: dict) -> str:
            total = sum(counts.values()) or 1
            bars = ""
            for name, cnt in sorted(counts.items(), key=lambda x: -x[1]):
                pct = int(cnt / total * 100)
                bars += f"""
                <div style='margin:4px 0'>
                  <span style='display:inline-block;width:100px;color:#555'>{escape(str(name))}</span>
                  <span style='display:inline-block;background:#41b883;width:{pct * 2}px;height:14px;vertical-align:middle'></span>
                  <span style='color:#888;font-size:12px'> {cnt}件 ({pct}%)</span>
                </div>"""
            return bars

        summary_html = _md_to_html_basic(trend_summary)

        return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:900px;margin:0 auto;padding:20px;color:#333;background:#f9f9f9">

<div style="background:#fff;border-radius:8px;padding:24px;margin-bottom:20px;box-shadow:0 2px 4px rgba(0,0,0,.08)">
  <h1 style="color:#1a1a1a;font-size:22px;margin:0 0 6px">週次トレンドレポート</h1>
  <p style="color:#888;margin:0">{date_str} 自動収集 ／ note・はてブ</p>
</div>

<!-- AIサマリー -->
<div style="background:#fff;border-radius:8px;padding:24px;margin-bottom:20px;box-shadow:0 2px 4px rgba(0,0,0,.08)">
  {summary_html}
</div>

<!-- note人気記事 -->
<div style="background:#fff;border-radius:8px;padding:24px;margin-bottom:20px;box-shadow:0 2px 4px rgba(0,0,0,.08)">
  <h2 style="color:#41b883;font-size:18px;margin:0 0 16px">note 収集記事</h2>
  <p>集計 {len(note_articles)}件 ／ 掲載 {min(len(note_articles), 20)}件。指定タグから取得できた範囲であり、note全体の順位・売上・今週の伸びを示すものではありません。</p>
  <div style="margin-bottom:12px">
    <strong>タイトルパターン</strong><br>{pattern_bars(note_stats.title_pattern_counts)}
    <br><strong>有料化位置（有料記事）:</strong> {
      ", ".join(f"{escape(str(PAID_POS_LABEL.get(k,k)))}:{v}件" for k,v in note_stats.paid_position_counts.items()) or "データなし"
    }<br>
    <strong>公開部分の平均見出し数:</strong> {str(note_stats.avg_heading_count) + '個' if note_stats.avg_heading_count is not None else '未取得'}
    （本文取得済み {note_stats.heading_sample_count}件のみ。未取得はゼロ扱いせず除外。有料部分は対象外）
  </div>
  <table style="width:100%;border-collapse:collapse">
    <thead>
      <tr style="background:#f5f5f5">
        <th style="padding:8px;text-align:left">記事</th>
        <th style="padding:8px;text-align:left">分析</th>
        <th style="padding:8px;text-align:left">見出し構成</th>
      </tr>
    </thead>
    <tbody>{note_rows}</tbody>
  </table>
</div>

<!-- はてブ -->
<div style="background:#fff;border-radius:8px;padding:24px;margin-bottom:20px;box-shadow:0 2px 4px rgba(0,0,0,.08)">
  <h2 style="color:#0078d4;font-size:18px;margin:0 0 16px">はてブ ホットエントリ（ビジネス・キャリア系）</h2>
  <p>集計 {len(hatena_entries)}件 ／ 掲載 {min(len(hatena_entries), 15)}件。指定RSS・絞り込み条件・取得上限内の候補です。</p>
  <div style="margin-bottom:12px">
    <strong>タイトルパターン</strong><br>{pattern_bars(hatena_stats.title_pattern_counts)}
  </div>
  <table style="width:100%;border-collapse:collapse">
    <thead>
      <tr style="background:#f5f5f5">
        <th style="padding:8px;text-align:left">記事</th>
        <th style="padding:8px;text-align:left">分析</th>
      </tr>
    </thead>
    <tbody>{hatena_rows}</tbody>
  </table>
</div>

<p style="color:#bbb;font-size:11px;text-align:center">このメールはnote_trend_collectorにより自動生成されました</p>
</body></html>"""
