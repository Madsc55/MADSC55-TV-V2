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

    def test_only_fresh_decoded_av_is_accepted_as_inventory_proof(self):
        accepted = {"decoded_av_verified": True, "decode_status": "DECODED_AV"}
        self.assertTrue(scanner.current_decode_confirmed(accepted, "AV_VERIFIED"))
        for row, status in (
                ({}, "AV_VERIFIED"),
                ({"decoded_av_verified": "true", "decode_status": "DECODED_AV"}, "AV_VERIFIED"),
                ({"decoded_av_verified": True, "decode_status": "NO_DECODED_FRAME"}, "AV_VERIFIED"),
                (accepted, "UNVERIFIED_OR_FAILED"),
                (None, "AV_VERIFIED")):
            with self.subTest(row=row, status=status):
                self.assertFalse(scanner.current_decode_confirmed(row, status))

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

    def test_integrated_discovery_admits_only_new_https_m3u_sources(self):
        report = {"candidates": [
            {"source": "m3u", "url": "https://lists.example.net/world.m3u", "verified_av": False},
            {"source": "m3u", "url": "http://lists.example.net/insecure.m3u", "verified_av": False},
            {"source": "youtube", "url": "https://www.youtube.com/watch?v=abcdefghijk", "verified_av": False},
            {"source": "m3u", "url": "https://lists.example.net/world.m3u", "verified_av": False},
            None,
        ]}
        existing = [{"id": "configured", "url": "https://lists.example.net/already.m3u"}]
        accepted, rejected = scanner.normalize_integrated_m3u_sources(report, existing)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["url"], "https://lists.example.net/world.m3u")
        self.assertEqual(accepted[0]["scope"], "candidate")
        self.assertEqual(len(rejected), 3)

    def test_integrated_discovery_rejects_invalid_root_and_verified_claims(self):
        for report in (None, [], {"candidates": {}}, {"candidates": None}):
            with self.assertRaises(ValueError):
                scanner.normalize_integrated_m3u_sources(report, [])
        report = {"candidates": [
            {"source": "m3u", "url": "https://lists.example.net/a.m3u", "verified_av": True},
            {"source": "m3u", "url": "https://user:pass@lists.example.net/b.m3u", "verified_av": False},
        ]}
        accepted, rejected = scanner.normalize_integrated_m3u_sources(report, [])
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), 2)

if __name__ == "__main__":
    unittest.main()
