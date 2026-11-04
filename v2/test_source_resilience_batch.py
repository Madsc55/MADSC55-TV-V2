#!/usr/bin/env python3
"""Grouped offline regressions for resilient V2 public-source discovery."""
import unittest

from github_source_discovery import eligible_playlist_path, error_summary as github_errors, error_kind as github_kind
from run_live_page_discovery import safe_page_redirect, scan, error_kind as page_kind
from youtube_discovery import metadata_summary, failure_reason
from document_platform_discovery import MAX_DOCS, ARCHIVE_SEARCH
from run_forge_source_discovery import error_summary as forge_errors
from urllib.error import HTTPError


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

    def test_error_buckets_never_include_urls_or_secrets(self):
        exc = HTTPError("https://example.org/private?token=secret", 403, "forbidden", {}, None)
        self.assertEqual(github_kind(exc), "HTTP_403")
        self.assertEqual(page_kind(exc), "HTTP_403")
        self.assertEqual(github_errors([
            {"repository": "a/gist", "error": "HTTP_403"},
            {"query": "test", "error": "HTTP_429"}]),
            {"gist:HTTP_403": 1, "search:HTTP_429": 1})
        self.assertEqual(forge_errors([
            {"forge": "gitlab", "error": "HTTP_403"}]), {"gitlab:HTTP_403": 1})
        report = scan([{"id": "foo", "url": "https://example.org/live"}],
                      fetcher=lambda _: (_ for _ in ()).throw(exc))
        self.assertEqual(report["anonymous_error_summary"], {"HTTP_403": 1})
        self.assertNotIn("secret", str(report))

    def test_youtube_unverified_is_not_playback(self):
        self.assertEqual(failure_reason("Sign in to confirm you're not a bot"), "BOT_CHALLENGE")
        self.assertEqual(failure_reason("HTTP Error 429"), "RATE_LIMITED")
        self.assertEqual(failure_reason("video unavailable"), "VIDEO_UNAVAILABLE")
        self.assertEqual(failure_reason(""), "EXTRACTOR_FAILED")

    def test_archive_public_metadata_query_remains_bounded(self):
        self.assertEqual(MAX_DOCS, 24)
        self.assertIn("rows=48", ARCHIVE_SEARCH)
        self.assertIn("archive.org/advancedsearch.php?", ARCHIVE_SEARCH)


    def test_live_page_retries_transient_503_without_retrying_403(self):
        import io
        from unittest.mock import patch
        from urllib.error import HTTPError
        import run_live_page_discovery as live
        class FakeOpener:
            calls = 0
            def open(self, request, timeout=12):
                self.calls += 1
                if self.calls == 1:
                    raise HTTPError(request.full_url, 503, "transient", {}, None)
                return io.BytesIO(b'<html><a href="/live/">live</a></html>')
        opener = FakeOpener()
        with patch("urllib.request.build_opener", return_value=opener), \
             patch.object(live.time, "sleep", return_value=None):
            self.assertIn("<html>", live.fetch_page("https://example.org/"))
        self.assertEqual(opener.calls, 2)
        class AlwaysForbidden:
            calls = 0
            def open(self, request, timeout=12):
                self.calls += 1
                raise HTTPError(request.full_url, 403, "blocked", {}, None)
        blocked = AlwaysForbidden()
        with patch("urllib.request.build_opener", return_value=blocked), \
             patch.object(live.time, "sleep", return_value=None):
            with self.assertRaises(HTTPError):
                live.fetch_page("https://example.org/")
        self.assertEqual(blocked.calls, 1)

if __name__ == "__main__":
    unittest.main()
