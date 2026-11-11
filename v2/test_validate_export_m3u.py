#!/usr/bin/env python3
"""Offline regression tests for read-only export syntax validation."""
import unittest
from validate_export_m3u import validate_m3u


def playlist(*entries):
    return "#EXTM3U\n" + "".join(
        f'#EXTINF:-1 group-title="TEST",Channel {i}\n{url}\n'
        for i, url in enumerate(entries, 1)
    )


class ExportM3UTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_m3u(playlist("https://example.org/a.m3u8")), [])

    def test_empty(self):
        self.assertIn("missing exact #EXTM3U header", validate_m3u(""))

    def test_missing_group(self):
        self.assertTrue(any("group-title" in e for e in
                            validate_m3u("#EXTM3U\n#EXTINF:-1,Channel\nhttps://example.org/a\n")))

    def test_empty_group(self):
        self.assertTrue(any("empty group-title" in e for e in
                            validate_m3u('#EXTM3U\n#EXTINF:-1 group-title="",Channel\nhttps://example.org/a\n')))

    def test_duplicate_stream(self):
        self.assertTrue(any("duplicate stream URL" in e for e in
                            validate_m3u(playlist("https://example.org/a", "https://example.org/a"))))

    def test_missing_url(self):
        self.assertTrue(any("no URL" in e for e in
                            validate_m3u('#EXTM3U\n#EXTINF:-1 group-title="TEST",Channel\n')))

    def test_reject_embedded_hls_manifest(self):
        content = ('#EXTM3U\n#EXTINF:-1 group-title="TEST",Channel\n'
                   '#EXT-X-STREAM-INF:BANDWIDTH=1000000\nhttps://example.org/a.m3u8\n')
        self.assertTrue(any("HLS manifest directive" in e for e in validate_m3u(content)))

    def test_invalid_scheme(self):
        self.assertTrue(any("unsupported URL scheme" in e for e in
                            validate_m3u(playlist("file:///etc/passwd"))))

    def test_reject_malformed_http_url(self):
        for url in ("https://", "https://example.org:bogus/a", "https://example.org/a b"):
            with self.subTest(url=url):
                self.assertTrue(any("invalid or unsafe stream URL" in e
                                    for e in validate_m3u(playlist(url))))

    def test_group_title_must_be_unambiguous(self):
        content = ('#EXTM3U\n#EXTINF:-1 group-title="One" group-title="Two",Channel\n'
                   'https://example.org/a\n')
        self.assertTrue(any("duplicate or empty group-title" in e for e in validate_m3u(content)))

    def test_quoted_comma_in_metadata_and_channel_name(self):
        content = ('#EXTM3U\n#EXTINF:-1 tvg-name="One, Two" group-title="TEST",One, Two\n'
                   'https://example.org/a\n')
        self.assertEqual(validate_m3u(content), [])

    def test_orphan_url(self):
        self.assertTrue(any("without EXTINF" in e for e in
                            validate_m3u("#EXTM3U\nhttps://example.org/a\n")))


if __name__ == "__main__":
    unittest.main()
