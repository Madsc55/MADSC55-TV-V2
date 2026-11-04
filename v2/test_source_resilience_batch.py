#!/usr/bin/env python3
"""Grouped offline regressions for resilient V2 public-source discovery."""
import unittest

from github_source_discovery import eligible_playlist_path
from run_live_page_discovery import safe_page_redirect
from youtube_discovery import metadata_summary
from document_platform_discovery import MAX_DOCS, ARCHIVE_SEARCH


class SourceResilienceBatch(unittest.TestCase):
    def test_github_playlist_path_screening(self):
        self.assertTrue(eligible_playlist_path("tr/channels.m3u"))
        self.assertTrue(eligible_playlist_path("az/live.m3u8"))
        self.assertTrue(eligible_playlist_path("tv-playlist.txt"))
        self.assertTrue(eligible_playlist_path("iptv-tr.txt"))
        for path in ("README.txt", "licenses/COPYING.txt", "../secrets.m3u",
                     "/private.m3u", "a\\b.m3u", "channels.json"):
            with self.subTest(path=path):
                self.assertFalse(eligible_playlist_path(path))

    def test_public_www_redirect_without_foreign_origin(self):
        self.assertTrue(safe_page_redirect(
            "https://www.example.org/live", "https://example.org/live/"))
        self.assertTrue(safe_page_redirect(
            "https://example.org/live", "https://www.example.org/live"))
        for target in ("http://example.org/live", "https://localhost/live",
                       "https://www.other.org/live",
                       "https://user:secret@example.org/live",
                       "https://example.org:8080/live",
                       "https://example.org/live?token=secret"):
            with self.subTest(target=target):
                self.assertFalse(safe_page_redirect("https://example.org/", target))

    def test_youtube_verification_is_not_inferred(self):
        rows = [{"status": status} for status in (
            "LIVE_METADATA_VERIFIED", "NOT_CURRENTLY_LIVE",
            "UNVERIFIED", "DISCOVERED_NOT_LIVE_VERIFIED")]
        result = metadata_summary(rows)
        self.assertEqual(result["metadata_verification_attempted"], 3)
        self.assertEqual(result["metadata_unverified_count"], 1)
        self.assertEqual(result["metadata_unattempted_count"], 1)
        self.assertFalse(result["metadata_coverage_complete"])
        self.assertTrue(metadata_summary([
            {"status": "LIVE_METADATA_VERIFIED"}])["metadata_coverage_complete"])

    def test_archive_public_metadata_query_remains_bounded(self):
        self.assertEqual(MAX_DOCS, 24)
        self.assertIn("rows=48", ARCHIVE_SEARCH)
        self.assertIn("archive.org/advancedsearch.php?", ARCHIVE_SEARCH)


if __name__ == "__main__":
    unittest.main()
