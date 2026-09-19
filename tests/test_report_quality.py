import unittest
from unittest.mock import Mock

from analyzer import ContentAnalyzer
from collectors.note_collector import NoteArticle, NoteCollector
from mailer import EmailSender, _md_to_html_basic
from bs4 import BeautifulSoup


class ReportQualityTests(unittest.TestCase):
    def article(self, **kwargs):
        return NoteArticle("例", "https://note.com/test/n/n1", "著者", "仕事", **kwargs)

    def test_unknown_is_excluded_but_known_zero_is_included(self):
        _, stats = ContentAnalyzer().analyze_note_articles([
            self.article(), self.article(details_fetched=True),
            self.article(details_fetched=True, headings=["h2: A", "h2: B"]),
        ])
        self.assertEqual(stats.avg_heading_count, 1.0)
        self.assertEqual(stats.heading_sample_count, 2)

    def test_all_unknown_has_no_average(self):
        _, stats = ContentAnalyzer().analyze_note_articles([self.article()])
        self.assertIsNone(stats.avg_heading_count)
        self.assertEqual(stats.heading_sample_count, 0)

    def test_empty_sample_has_no_average(self):
        _, stats = ContentAnalyzer().analyze_note_articles([])
        self.assertIsNone(stats.avg_heading_count)

    def test_missing_body_does_not_succeed(self):
        collector = NoteCollector()
        collector.session.get = Mock(return_value=Mock(text="<html>Not available</html>"))
        article = self.article()
        with self.assertRaises(ValueError):
            collector._enrich_article(article)
        self.assertFalse(article.details_fetched)

    def test_body_without_headings_is_known_zero(self):
        collector = NoteCollector()
        collector.session.get = Mock(return_value=Mock(text='<div data-testid="note-body"><p>本文</p></div>'))
        article = self.article()
        collector._enrich_article(article)
        self.assertTrue(article.details_fetched)
        self.assertEqual(article.headings, [])

    def test_heading_count_is_not_capped_at_fifteen(self):
        collector = NoteCollector()
        collector.session.get = Mock(return_value=Mock(text='<div data-testid="note-body">' + '<h2>見出し</h2>' * 18 + '</div>'))
        article = self.article()
        collector._enrich_article(article)
        self.assertEqual(len(article.headings), 18)

    def test_email_distinguishes_unknown_and_discloses_sample(self):
        analyzer = ContentAnalyzer()
        html = EmailSender()._build_html(
            analyzer.analyze_note_articles([self.article()]),
            analyzer.analyze_hatena_entries([]), "テスト用",
        )
        self.assertIn("公開部分の見出し:</strong> 未取得", html)
        self.assertIn("集計 1件 ／ 掲載 1件", html)
        self.assertIn("本文取得済み 0件のみ", html)
        self.assertNotIn("h0まで", html)

    def test_plaintext_contains_source_and_scope(self):
        analyzer = ContentAnalyzer()
        article = self.article()
        article.url = "https://note.com/test/n/n1?a=1&b=2"
        result = EmailSender()._build_plain(
            analyzer.analyze_note_articles([article]),
            analyzer.analyze_hatena_entries([]), "収集警告\n分析本文",
        )
        self.assertTrue(result.startswith("収集警告\n分析本文"))
        self.assertIn(article.url, result)
        self.assertIn("[N1]", result)
        self.assertIn("集計 1件 ／ 掲載 1件", result)

    def test_plaintext_rejects_unsafe_source(self):
        analyzer = ContentAnalyzer()
        article = self.article()
        article.url = "javascript:alert(1)"
        result = EmailSender()._build_plain(
            analyzer.analyze_note_articles([article]),
            analyzer.analyze_hatena_entries([]), "分析本文",
        )
        self.assertNotIn("javascript:", result)
        self.assertIn("安全な出典URLを取得できません", result)

    def test_markdown_list_has_valid_parent(self):
        html = _md_to_html_basic("- A\n* B\n\n本文\n- C")
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(len(soup.find_all("ul")), 2)
        self.assertEqual(len(soup.find_all("li")), 3)
        self.assertTrue(all(li.parent.name == "ul" for li in soup.find_all("li")))

    def test_html_source_ids_match_prompt(self):
        analyzer = ContentAnalyzer()
        from collectors.hatena_collector import HatenaEntry
        result = EmailSender()._build_html(
            analyzer.analyze_note_articles([self.article()]),
            analyzer.analyze_hatena_entries([HatenaEntry("例", "https://example.com", "")]),
            "出典 N1 / H1",
        )
        self.assertIn("[N1]", result)
        self.assertIn("[H1]", result)


if __name__ == "__main__":
    unittest.main()
