#!/usr/bin/env python3
"""Public candidate report must never expose URL tokens through M3U metadata."""
import unittest
from discover import discover, public_metadata

class MetadataRedactionTests(unittest.TestCase):
    def test_redacts_url_and_token_fields(self):
        for value in ("token=SECRET123", "apikey:SECRET123",
                      "https://example.org/image.png?token=SECRET123"):
            self.assertNotIn("SECRET123", public_metadata(value))
    def test_candidate_public_report_redacts_metadata(self):
        data = ('#EXTM3U\n'
                '#EXTINF:-1 tvg-id="tr.example" tvg-logo="https://example.org/logo.png?token=SECRET123" group-title="token=SECRET123",TRT token=SECRET123\n'
                'https://example.org/live.m3u8?token=SECRET123\n')
        report = discover([("source", data)], "#EXTM3U\n", {"source": "TR"})
        self.assertEqual(len(report), 1)
        self.assertNotIn("SECRET123", str(report))
        self.assertIn("url_sha256", report[0])
if __name__ == "__main__":
    unittest.main(verbosity=2)
