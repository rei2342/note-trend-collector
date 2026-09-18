import json
import os
import ssl
import unittest
from email import message_from_string
from unittest.mock import patch, MagicMock
from analyzer import AnalyzedNote, PatternStats
from mailer import EmailSender, _safe_url, _md_to_html_basic
import summarizer
import main


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.empty = ([], PatternStats())
        self.article = AnalyzedNote(
            title='<img src=x onerror="bad()">', url='javascript:alert(1)',
            author='<b>name</b>', tag='<script>tag</script>',
            description='<iframe src=x>', headings=['<img src=x>'],
        )
        self.notes = ([self.article], PatternStats(title_pattern_counts={"<img src=x>": 1}))

    def test_untrusted_html_escaped(self):
        result = EmailSender()._build_html(self.notes, self.empty, "# <script>bad</script>")
        for bad in ("<script>", "<img ", "<iframe", "javascript:"):
            self.assertNotIn(bad, result)
        self.assertIn("&lt;img", result)

    def test_markdown_escapes_html_before_formatting(self):
        result = _md_to_html_basic("**<img src=x>**\n### <script>x</script>")
        self.assertIn("<strong>&lt;img", result)
        self.assertNotIn("<script>", result)

    def test_urls(self):
        for value in ("javascript:x", "data:text/html,x", "//evil.test", "https://", "https://a b", "https://user@host", "https://["):
            self.assertEqual(_safe_url(value), "#")
        self.assertEqual(_safe_url('https://example.com/?a=1&b=2'), 'https://example.com/?a=1&amp;b=2')

    def test_empty_data_does_not_call_api(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-not-a-key"}), patch.object(summarizer, "_call_claude_api") as api:
            result = summarizer.TrendSummarizer().generate_summary(self.empty, self.empty)
        api.assert_not_called()
        self.assertIn("データ不足", result)
        self.assertNotIn("今週の主役", result)

    def test_api_failure_explicit_fallback(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-not-a-key"}), patch.object(summarizer, "_call_claude_api", return_value=""):
            result = summarizer.TrendSummarizer().generate_summary(self.notes, self.empty)
        self.assertIn("未実施または失敗", result)
        self.assertIn("はてブデータは未取得", result)

    def test_prompt_has_sources_and_no_prediction_request(self):
        result = summarizer._build_analysis_prompt(*self.notes, *self.empty)
        self.assertIn('"source_id": "N1"', result)
        self.assertIn('"url":', result)
        self.assertNotIn("想定いいね数", result)

    def test_truncated_api_response_rejected(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"stop_reason": "max_tokens", "content": [{"type": "text", "text": "unfinished"}]}
        ).encode()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-not-a-key"}), patch("urllib.request.urlopen", return_value=response):
            self.assertEqual(summarizer._call_claude_api("test"), "")

    def test_multi_text_blocks(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"stop_reason": "end_turn", "content": [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}]}
        ).encode()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-not-a-key"}), patch("urllib.request.urlopen", return_value=response):
            self.assertEqual(summarizer._call_claude_api("test"), "one\ntwo")

    def test_mail_tls_timeout_and_plaintext(self):
        with patch("mailer.config.GMAIL_ADDRESS", "sender@example.com"), patch("mailer.config.GMAIL_APP_PASSWORD", "dummy"), patch("mailer.config.REPORT_TO_EMAILS", ["recipient@example.com"]), patch("mailer.smtplib.SMTP") as smtp:
            EmailSender().send_weekly_report(self.empty, self.empty, "summary")
        smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
        server = smtp.return_value.__enter__.return_value
        ctx = server.starttls.call_args.kwargs["context"]
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        message = message_from_string(server.sendmail.call_args.args[2])
        self.assertEqual([p.get_content_type() for p in message.get_payload()], ["text/plain", "text/html"])

    def test_zero_collection_stops_delivery(self):
        with patch("main.validate_config"), patch("main.NoteCollector") as note, patch("main.HatenaCollector") as hatena, patch("main.EmailSender") as sender:
            note.return_value.collect.return_value = []
            hatena.return_value.collect.return_value = []
            with self.assertRaises(RuntimeError):
                main.main()
        sender.assert_not_called()


if __name__ == "__main__":
    unittest.main()
