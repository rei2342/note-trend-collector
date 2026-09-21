import unittest
from unittest.mock import Mock
from analyzer import ContentAnalyzer
from collectors.note_collector import NoteArticle, NoteCollector
from mailer import EmailSender

class RemovedPaywallMetricTests(unittest.TestCase):
    def test_public_markup_does_not_create_paid_body_position(self):
        collector = NoteCollector()
        collector.session.get = Mock(return_value=Mock(text='<div data-testid="note-body"><h2>見出し</h2><p>内容</p><div>続きをみるには</div></div>'))
        item = NoteArticle("例", "https://example.invalid", "著者", "仕事", is_paid=True, paid_position="early")
        collector._enrich_article(item)
        self.assertIsNone(item.paid_position)

    def test_old_position_fields_still_load_but_are_not_reported(self):
        analyzer = ContentAnalyzer()
        notes = analyzer.analyze_note_articles([NoteArticle("例", "https://example.invalid", "著者", "仕事", is_paid=True, paid_position="middle")])
        self.assertEqual(notes[1].paid_position_counts, {})
        self.assertNotIn("有料化", notes[0][0].structure_summary)
        html = EmailSender()._build_html(notes, analyzer.analyze_hatena_entries([]), "summary")
        self.assertNotIn("有料化", html)
        self.assertIn("有料", html)


if __name__ == "__main__":
    unittest.main()
