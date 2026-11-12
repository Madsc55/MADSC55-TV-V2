#!/usr/bin/env python3
"""Network-free checks for opt-in platform search adapters."""
import unittest
from stage6_platform_search import ENDPOINTS, extract, request_url

class Stage6PlatformSearchTests(unittest.TestCase):
    def test_all_platforms_have_https_api(self):
        self.assertEqual(set(ENDPOINTS), {"github", "gitlab", "codeberg", "gist"})
        for platform in ENDPOINTS:
            self.assertTrue(request_url(platform, "tr.m3u8").startswith("https://"))

    def test_queries_are_bounded(self):
        for value in (0, 51):
            with self.assertRaises(ValueError):
                request_url("github", "tr.m3u8", per_page=value)
        with self.assertRaises(ValueError):
            request_url("unknown", "tr.m3u8")

    def test_github_and_codeberg_metadata(self):
        self.assertEqual(len(extract("github", {"items": [{"html_url": "https://github.com/x/y"}]}, "tr")), 1)
        self.assertEqual(len(extract("codeberg", {"data": [{"html_url": "https://codeberg.org/x/y"}]}, "tr")), 1)
        self.assertEqual(extract("gitlab", [{"web_url": "http://unsafe"}], "tr"), [])

    def test_gist_only_m3u_files(self):
        data = [{"html_url": "https://gist.github.com/a/1", "files": {"a": {"filename": "a.txt"}}},
                {"html_url": "https://gist.github.com/a/2", "files": {"a": {"filename": "tr.m3u8"}}}]
        self.assertEqual(len(extract("gist", data, "recent")), 1)

if __name__ == "__main__":
    unittest.main()
