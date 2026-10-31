#!/usr/bin/env python3
"""No-network tests for approved live-page reference discovery."""
import unittest
from run_live_page_discovery import approved_page, scan

class LivePageRunnerTests(unittest.TestCase):
    def test_only_public_credential_free_origins(self):
        self.assertTrue(approved_page("https://example.org/live"))
        for url in ("http://example.org/live", "https://localhost/live",
                    "https://127.0.0.1/live", "https://user:pass@example.org/live",
                    "https://example.org:8080/live", "https://example.org/live?token=abc"):
            with self.subTest(url=url):
                self.assertFalse(approved_page(url))
    def test_extract_reference_hashes_without_leaking_token(self):
        page = [{"id": "official-1", "url": "https://example.org/live"}]
        report = scan(page, lambda url: '<a href="https://www.youtube.com/watch?v=abc123&token=secret">Live</a>')
        self.assertEqual(len(report["references"]), 1)
        self.assertNotIn("token=secret", str(report))
        self.assertFalse(report["playback_verified"])
    def test_reject_private_page_without_fetch(self):
        report = scan([{"id": "bad", "url": "https://localhost/live"}],
                      lambda url: self.fail("Network must not be called"))
        self.assertEqual(report["errors"][0]["error"], "UNSAFE_PAGE")
        self.assertEqual(report["coverage_status"], "PARTIAL_APPROVED_PAGES")
    def test_partial_page_failure_keeps_successful_references(self):
        pages = [{"id": "good", "url": "https://example.org/live"},
                 {"id": "bad", "url": "https://example.org/unavailable"}]
        def fetch(url):
            if url.endswith("unavailable"):
                raise OSError("offline")
            return '<a href="https://www.youtube.com/watch?v=abc123">Live</a>'
        report = scan(pages, fetch)
        self.assertEqual(len(report["references"]), 1)
        self.assertEqual(report["coverage_status"], "PARTIAL_APPROVED_PAGES")
        self.assertEqual(len(report["errors"]), 1)
    def test_empty_inventory_is_safe(self):
        self.assertEqual(scan([])["pages_checked"], 0)
        self.assertEqual(scan([])["coverage_status"], "NO_APPROVED_PAGES")
    def test_refuse_silent_truncation(self):
        pages = [{"id": str(i), "url": "https://example.org/live"} for i in range(101)]
        with self.assertRaisesRegex(ValueError, "100-page"):
            scan(pages, lambda url: self.fail("Must not fetch when inventory exceeds limit"))
if __name__ == "__main__":
    unittest.main(verbosity=2)
