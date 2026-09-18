import unittest
from unittest.mock import patch, Mock
import requests
from collectors.hatena_collector import HatenaCollector, HatenaEntry


class CollectionTests(unittest.TestCase):
    def test_rss_uses_timeout_and_http_status(self):
        collector = HatenaCollector()
        response = Mock(content=b'<?xml version="1.0"?><rss version="2.0"><channel><title>test</title></channel></rss>')
        collector.session.get = Mock(return_value=response)
        self.assertEqual(collector._fetch_rss("business"), [])
        self.assertIn("timeout", collector.session.get.call_args.kwargs)
        response.raise_for_status.assert_called_once()

    def test_http_failure_is_not_empty_success(self):
        collector = HatenaCollector()
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("503")
        collector.session.get = Mock(return_value=response)
        with self.assertRaises(requests.HTTPError):
            collector._fetch_rss("business")

    def test_malformed_feed_rejected(self):
        collector = HatenaCollector()
        collector.session.get = Mock(return_value=Mock(content=b"<broken"))
        with self.assertRaises(ValueError):
            collector._fetch_rss("business")

    def test_duplicate_categories_fetched_once(self):
        collector = HatenaCollector()
        with patch("config.HATENA_CATEGORIES", ["business", "economics"]), patch.object(collector, "_fetch_rss", return_value=[]) as fetch, patch("time.sleep"):
            collector.collect()
        fetch.assert_called_once_with("business")

    def test_failed_count_is_unknown_not_zero(self):
        collector = HatenaCollector()
        entry = HatenaEntry("仕事", "https://example.com", "")
        collector.session.get = Mock(return_value=Mock(text="error"))
        with self.assertRaises(ValueError):
            collector._enrich_bookmark_count(entry)
        self.assertIsNone(entry.bookmark_count)

    def test_zero_is_valid(self):
        collector = HatenaCollector()
        entry = HatenaEntry("仕事", "https://example.com", "")
        collector.session.get = Mock(return_value=Mock(text="0"))
        collector._enrich_bookmark_count(entry)
        self.assertEqual(entry.bookmark_count, 0)

    def test_candidate_limit_and_unknown_sorted_last(self):
        collector = HatenaCollector()
        entries = [HatenaEntry("仕事", f"https://example.com/{i}", "") for i in range(3)]
        def enrich(entry):
            if entry is entries[1]:
                entry.bookmark_count = 0
        with patch("config.HATENA_CATEGORIES", ["economics"]), patch("config.HATENA_ENTRIES_COUNT", 2), patch.object(collector, "_fetch_rss", return_value=entries), patch.object(collector, "_enrich_bookmark_count", side_effect=enrich), patch("time.sleep"):
            result = collector.collect()
        self.assertEqual(result, [entries[1], entries[0]])
