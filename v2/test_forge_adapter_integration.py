#!/usr/bin/env python3
"""Offline regression tests for approved forge discovery sources."""
import hashlib
import unittest
from forge_source_review import normalize, approved_sources


class ForgeAdapterIntegrationTests(unittest.TestCase):
    def test_both_report_url_fields_are_supported(self):
        urls = [
            "https://codeberg.org/example/tv/raw/branch/main/channels.m3u",
            "https://gitlab.com/api/v4/projects/42/repository/files/tv.m3u/raw?ref=main",
        ]
        report = {"schema": 1, "sources": [
            {"forge": "codeberg", "url": urls[0]},
            {"forge": "gitlab", "source_url": urls[1]},
        ]}
        self.assertEqual({x["url"] for x in normalize(report)}, set(urls))
        self.assertEqual(len(approved_sources(report, {hashlib.sha256(urls[0].encode()).hexdigest()})), 1)

    def test_mismatched_origin_is_not_promoted(self):
        report = {"schema": 1, "sources": [
            {"forge": "gitlab", "url": "https://codeberg.org/example/tv/raw/branch/main/channels.m3u"},
            {"forge": "codeberg", "url": "https://gitlab.com/api/v4/projects/42/repository/files/tv.m3u/raw?ref=main"},
        ]}
        self.assertEqual(normalize(report), [])

    def test_duplicate_sources_are_not_promoted_twice(self):
        url = "https://codeberg.org/example/tv/raw/branch/main/channels.m3u"
        report = {"schema": 1, "sources": [{"forge": "codeberg", "url": url}, {"forge": "codeberg", "source_url": url}]}
        self.assertEqual(len(normalize(report)), 1)


if __name__ == "__main__":
    unittest.main()
