#!/usr/bin/env python3
import unittest
from reference_classifier import classify_reference

class ReferenceClassifierTests(unittest.TestCase):
    def test_youtube_is_not_stream(self):
        for url in ("https://www.youtube.com/watch?v=abc123",
                    "https://www.youtube.com/@trthaber/live",
                    "https://youtu.be/abc123"):
            item = classify_reference(url)
            self.assertTrue(item["kind"].startswith("youtube"))
            self.assertFalse(item["playable_stream"])
    def test_playlist_is_only_source(self):
        item = classify_reference("https://example.org/tr.m3u8")
        self.assertEqual(item["kind"], "playlist-source")
        self.assertFalse(item["playable_stream"])
    def test_credentials_and_http_rejected(self):
        self.assertIsNone(classify_reference("http://example.org/tr.m3u"))
        self.assertIsNone(classify_reference("https://user:pass@example.org/tr.m3u"))
if __name__ == "__main__":
    unittest.main(verbosity=2)
