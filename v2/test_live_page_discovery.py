#!/usr/bin/env python3
import unittest
from live_page_discovery import live_reference, extract_live_references

class LivePageTests(unittest.TestCase):
    def test_youtube_pages_are_not_playback(self):
        html = ('<a href="https://www.youtube.com/@TRTHaber/live">Live</a>'
                '<a href="https://www.youtube.com/watch?v=abc123">Video</a>')
        refs = extract_live_references("https://example.org/official", html)
        self.assertEqual(len(refs), 2)
        self.assertTrue(all(x["playback_verified"] is False for x in refs))
    def test_private_and_http_rejected(self):
        for url in ("http://youtube.com/watch?v=abc", "https://localhost/live",
                    "https://127.0.0.1/live", "https://user:pass@example.org/live"):
            self.assertIsNone(live_reference(url))
    def test_dedup_and_relative_official(self):
        html = '<a href="/canli-yayin">Live</a><a href="/canli-yayin">Again</a>'
        refs = extract_live_references("https://example.org/index", html)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["kind"], "official-or-third-party-live-page")
    def test_private_origin_rejected(self):
        for url in ("https://127.0.0.1/index", "https://localhost/index",
                    "https://user:pass@example.org/index"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                extract_live_references(url, '<a href="/live">live</a>')
    def test_nonlive_pages_excluded(self):
        self.assertEqual(extract_live_references("https://example.org/index",
                                                 '<a href="/about">About</a>'), [])
if __name__ == "__main__":
    unittest.main(verbosity=2)
