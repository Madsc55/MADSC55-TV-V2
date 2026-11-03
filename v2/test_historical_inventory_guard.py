#!/usr/bin/env python3
"""Offline, bulk stage 3 tests. All stream URLs in tests are synthetic test fixtures."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from encrypted_archive import restore
from historical_inventory_guard import (SCHEMA, classify, identity, preserve_to_new_archive,
                                        reconcile)


class HistoricalInventoryGuardTests(unittest.TestCase):
    def test_4955_historical_rows_remain_preserved_without_synthetic_export(self):
        old = [{"url": "https://fixture.example.org/%04d.m3u8" % i,
                "name": "TRT %d" % i, "scope": "TR", "source": "#60"}
               for i in range(4951)]
        old.extend([
            {"url": old[0]["url"], "logo": "https://fixture.example.org/logo.png", "source": "older"},
            {"url_sha256": hashlib.sha256(b"only-hash").hexdigest(), "source": "#60"},
            {"anonymous_id": "historical-unknown"},
            {"url": "http://127.0.0.1/invalid.m3u8", "status": "HISTORICAL_FAILED"}
        ])
        self.assertEqual(len(old), 4955)
        new = [{"url": old[0]["url"], "source": "recent", "group": "Türkiye"},
               {"url": "https://fixture.example.org/new-az.m3u8", "tvg_id": "News.az"}]
        preserved, indexed, report = reconcile(old, new, 4955)
        self.assertEqual(preserved[:4955], old)
        self.assertEqual(report["historical_records_preserved"], 4955)
        self.assertEqual(report["historical_unique_real_urls"], 4951)
        self.assertEqual(report["historical_duplicate_url_rows"], 1)
        self.assertEqual(report["historical_hash_only_identities"], 1)
        self.assertEqual(report["historical_unidentified_records_preserved"], 2)
        self.assertEqual(report["unique_candidate_urls"], 4952)
        first = next(item for item in indexed if item["url"] == old[0]["url"])
        self.assertEqual(first["source_ids"], ["#60", "older", "recent"])
        self.assertTrue(first["historical_not_reverified"])
        self.assertFalse(first["device_verified"])
        self.assertFalse(report["historical_preservation_verified"])

    def test_tr_az_unknown_candidate_without_speech_claim(self):
        samples = [
            ({"scope": "AZ", "name": "News"}, "AZ", "SOURCE_GEO"),
            ({"tvg_id": "AzerTV.az", "name": "News"}, "AZ", "TVG_ID"),
            ({"name": "Azərbaycan TV"}, "AZ", "METADATA"),
            ({"scope": "TR", "name": "News"}, "TR", "SOURCE_GEO"),
            ({"tvg_id": "TRT1.tr"}, "TR", "TVG_ID"),
            ({"name": "Türk Haber"}, "TR", "METADATA"),
            ({"name": "Global News"}, "UNKNOWN", "NONE")
        ]
        for row, region, evidence in samples:
            with self.subTest(row=row):
                result = classify(row)
                self.assertEqual(result["region_candidate"], region)
                self.assertEqual(result["classification_evidence"], evidence)
                self.assertFalse(result["spoken_language_verified"])

    def test_missing_or_extra_history_fail_closed(self):
        rows = [{"url": "https://fixture.example.org/a.m3u8"}]
        with self.assertRaisesRegex(ValueError, "baseline"):
            reconcile(rows, [], 4955)
        with self.assertRaisesRegex(ValueError, "Missing historical"):
            reconcile([], [], 0)

    def test_exact_stream_urls_not_normalized_or_merged_by_name(self):
        old = [{"url": "https://fixture.example.org/a.m3u8?key=FIRST", "name": "TRT 1"},
               {"url": "https://fixture.example.org/a.m3u8?key=SECOND", "name": "TRT 1"}]
        _, indexed, report = reconcile(old)
        self.assertEqual(len(indexed), 2)
        self.assertEqual(report["historical_unique_real_urls"], 2)
        self.assertEqual(len({identity(row) for row in indexed}), 2)

    def test_hash_only_history_not_mistaken_for_restored_stream(self):
        url = "https://fixture.example.org/az.m3u8"
        old = [{"url_sha256": hashlib.sha256(url.encode()).hexdigest()},
               {"anonymous_id": "missing-url"}]
        preserved, indexed, report = reconcile(old, [])
        self.assertEqual(len(indexed), 0)
        self.assertEqual(len(preserved), 2)
        self.assertEqual(report["historical_identities_not_in_current"], 1)
        protected, indexed, report = reconcile(old, [{"url": url}])
        self.assertEqual(report["historical_hash_only_linked_to_real_urls"], 1)
        self.assertEqual(len(indexed), 1)
        self.assertEqual(len(protected), 3)
        self.assertTrue(indexed[0]["historical_not_reverified"])

    def test_encrypted_snapshot_restores_every_raw_row_and_deduplicated_view(self):
        old = [{"url": "https://fixture.example.org/a.m3u8", "source": "#60"},
               {"url": "https://fixture.example.org/a.m3u8", "logo": "old"},
               {"url_sha256": hashlib.sha256(b"lost").hexdigest()}]
        preserved, indexed, report = reconcile(old)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "historic.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
                self.assertTrue(preserve_to_new_archive(path, preserved, indexed))
                self.assertFalse(stat.S_IMODE(path.stat().st_mode) & 0o077)
                snapshot = restore(path)
                raw = [r for block in snapshot if block["kind"] == "raw_historical_and_new"
                       for r in block["records"]]
                view = [r for block in snapshot if block["kind"] == "deduplicated_view"
                        for r in block["records"]]
                self.assertEqual(raw, old)
                self.assertEqual(view, indexed)
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    preserve_to_new_archive(path, preserved, indexed)
        self.assertEqual(report["historical_records_preserved"], 3)


if __name__ == "__main__":
    unittest.main()
