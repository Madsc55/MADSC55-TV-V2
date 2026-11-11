#!/usr/bin/env python3
"""Offline scanner regression tests: no HTTP requests, no protected playlist edits."""
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import real_ibo_scan as scanner

class ScannerOfflineTests(unittest.TestCase):
    def test_m3u_metadata_and_dedup_source(self):
        payload = (b'#EXTM3U\n'
                   b'#EXTINF:-1 tvg-id="trt1.tr" tvg-logo="https://example.org/logo.png" group-title="Haber",TRT 1\n'
                   b'https://example.org/live.m3u8\n')
        entries = list(scanner.parse_m3u(payload))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["name"], "TRT 1")
        self.assertEqual(entries[0]["tvg_id"], "trt1.tr")
        self.assertEqual(entries[0]["group"], "Haber")
        self.assertEqual(entries[0]["logo"], "https://example.org/logo.png")

    def test_reject_non_m3u(self):
        with self.assertRaises(ValueError):
            list(scanner.parse_m3u(b'not an m3u'))

    def test_scope_is_not_language_proof(self):
        record = {"name": "Unspecified TV", "group": "", "tvg_id": ""}
        self.assertTrue(scanner.tr_az(record, "TR"))
        self.assertFalse(scanner.tr_az(record, "candidate"))
        self.assertFalse(scanner.tr_az({"name": "TRT World", "group": "", "tvg_id": ""}, "TR"))

    def test_invalid_hls_url_is_not_verified(self):
        self.assertIsNone(scanner.check_hls({"url": "file:///tmp/mock.m3u8"}, 1))

    def test_archive_entry_count_not_unique_url_count(self):
        sample = (b'#EXTM3U\n#EXTINF:-1,One\nhttps://example.org/same.m3u8\n'
                  b'#EXTINF:-1,Two\nhttps://example.org/same.m3u8\n')
        entries = list(scanner.parse_m3u(sample))
        self.assertEqual(len(entries), 2)
        self.assertEqual(len({x["url"] for x in entries}), 1)

if __name__ == "__main__":
    unittest.main()
