#!/usr/bin/env python3
"""No-network approved HTML index discovery tests."""
import unittest
from run_webpage_playlist_discovery import scan

class WebpagePlaylistRunnerTests(unittest.TestCase):
    def test_hashes_only_no_plaintext_urls(self):
        report = scan([{"id": "index-1", "url": "https://example.org/index"}],
                      lambda url: '<a href="/tr.m3u?token=SECRET123">TR</a>')
        self.assertEqual(len(report["references"]), 1)
        self.assertNotIn("SECRET123", str(report))
        self.assertTrue(report["references"][0]["review_required"])
        self.assertFalse(report["playback_verified"])
    def test_reject_private_without_fetch(self):
        report = scan([{"id": "bad", "url": "https://localhost/index"}],
                      lambda url: self.fail("No network allowed"))
        self.assertEqual(report["coverage_status"], "PARTIAL_APPROVED_PAGES")
    def test_empty_is_not_full_coverage(self):
        self.assertEqual(scan([])["coverage_status"], "NO_APPROVED_PAGES")
    def test_refuse_silent_inventory_truncation(self):
        with self.assertRaisesRegex(ValueError, "100 pages"):
            scan([{"id": str(i), "url": "https://example.org/index"} for i in range(101)])
if __name__ == "__main__":
    unittest.main(verbosity=2)
