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

    def test_historical_source_ids_preserve_both_formats(self):
        record = {"source_ids": ["new", "shared"], "source_id": "old"}
        self.assertEqual(scanner.historical_source_ids(record), ["new", "shared", "old"])
        self.assertEqual(scanner.historical_source_ids({"source_id": "old"}), ["old"])
        self.assertEqual(scanner.historical_source_ids({}), ["historical-archive"])
        with self.assertRaises(ValueError):
            scanner.historical_source_ids({"source_ids": "invalid"})

    def test_dynamic_source_report_skips_malformed_rows_and_deduplicates(self):
        status = "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"
        dynamic = {"sources": [None, 3, {"url": None, "status": status},
                              {"url": "http://example.org/a.m3u", "status": status},
                              {"url": "https://example.org/a.m3u", "status": status},
                              {"url": "https://example.org/a.m3u", "status": status}]}
        accepted, rejected = scanner.normalize_dynamic_sources(dynamic, [])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["url"], "https://example.org/a.m3u")
        self.assertEqual(len(rejected), 5)

    def test_dynamic_source_report_rejects_invalid_root(self):
        for value in (None, [], {"sources": {}}, {"sources": None}):
            with self.assertRaises(ValueError):
                scanner.normalize_dynamic_sources(value, [])

    def test_archive_entry_count_not_unique_url_count(self):
        sample = (b'#EXTM3U\n#EXTINF:-1,One\nhttps://example.org/same.m3u8\n'
                  b'#EXTINF:-1,Two\nhttps://example.org/same.m3u8\n')
        entries = list(scanner.parse_m3u(sample))
        self.assertEqual(len(entries), 2)
        self.assertEqual(len({x["url"] for x in entries}), 1)

    def test_worldwide_mode_includes_entries_without_tr_az_hints(self):
        record = {"name": "International News", "group": "World", "tvg_id": "news.int"}
        self.assertFalse(scanner.eligible_entry(record, "candidate", worldwide=False))
        self.assertTrue(scanner.eligible_entry(record, "candidate", worldwide=True))
        # Explicit TR/AZ exclusions remain active only in the default filtered mode.
        excluded = {"name": "TRT World", "group": "", "tvg_id": ""}
        self.assertFalse(scanner.eligible_entry(excluded, "TR", worldwide=False))
        self.assertTrue(scanner.eligible_entry(excluded, "TR", worldwide=True))

if __name__ == "__main__":
    unittest.main()
