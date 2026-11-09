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

    def test_duplicate_stream(self):
        self.assertTrue(any("duplicate stream URL" in e for e in
                            validate_m3u(playlist("https://example.org/a", "https://example.org/a"))))

    def test_missing_url(self):
        self.assertTrue(any("no URL" in e for e in
                            validate_m3u('#EXTM3U\n#EXTINF:-1 group-title="TEST",Channel\n')))

    def test_invalid_scheme(self):
        self.assertTrue(any("unsupported URL scheme" in e for e in
                            validate_m3u(playlist("file:///etc/passwd"))))

    def test_orphan_url(self):
        self.assertTrue(any("without EXTINF" in e for e in
                            validate_m3u("#EXTM3U\nhttps://example.org/a\n")))


if __name__ == "__main__":
    unittest.main()
