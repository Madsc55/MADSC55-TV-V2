#!/usr/bin/env python3
"""Offline source-fetch gate tests; never opens a network connection."""
import unittest
from unittest.mock import patch
from discover import fetch

class FetchSourceGateTests(unittest.TestCase):
    def test_rejects_private_and_http_without_network(self):
        with patch("urllib.request.build_opener", side_effect=AssertionError("network opened")):
            for url in ("http://example.org/tr.m3u", "https://localhost/tr.m3u",
                        "https://127.0.0.1/tr.m3u", "https://user:pass@example.org/tr.m3u"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    fetch(url)
    def test_gitlab_api_only_explicit_raw_file_pattern(self):
        with patch("urllib.request.build_opener", side_effect=RuntimeError("validated")):
            with self.assertRaisesRegex(RuntimeError, "validated"):
                fetch("https://gitlab.com/api/v4/projects/42/repository/files/tr.m3u/raw?ref=main")
            with self.assertRaises(ValueError):
                fetch("https://gitlab.com/api/v4/projects/42/repository/tree?ref=main")
if __name__ == "__main__":
    unittest.main(verbosity=2)
