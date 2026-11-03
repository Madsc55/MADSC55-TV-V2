#!/usr/bin/env python3
"""Stage-3 legacy history adapters: hash-only CSV and verified playback JSON."""
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import historical_inventory_guard as guard
from encrypted_archive import restore


class HistoricalLegacyImporterTests(unittest.TestCase):
    def test_hash_only_comparison_csv_is_retained_and_encrypted(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            csv_path = base / "old-not-retested.csv"
            first_hash = hashlib.sha256(b"old-decoded").hexdigest()
            with csv_path.open("w", encoding="utf-8", newline="") as out:
                w = csv.DictWriter(out, fieldnames=["url_sha256", "source", "name", "playback"])
                w.writeheader()
                w.writerow({"url_sha256": first_hash, "source": "#60",
                            "name": "Old Stream", "playback": "VIDEO_DECODED"})
                w.writerow({"url_sha256": first_hash, "source": "#60-retest",
                            "name": "Old Stream", "playback": "VIDEO_DECODED"})
            archive = base / "history.enc"
            summary = base / "report.json"
            argv = ["historical_inventory_guard.py", "--historical-csv", str(csv_path),
                    "--out-archive", str(archive), "--report", str(summary),
                    "--expected-historical-records", "2"]
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}), \
                 patch.object(sys, "argv", argv):
                guard.main()
                encrypted = restore(archive)
            raw = [row for block in encrypted if block.get("kind") == "raw_historical_and_new"
                   for row in block["records"]]
            self.assertEqual(len(raw), 2)
            self.assertEqual(raw[0]["url_sha256"], first_hash)
            data = json.loads(summary.read_text(encoding="utf-8"))
            self.assertTrue(data["historical_preservation_verified"])
            self.assertEqual(data["historical_unique_identities"], 1)
            self.assertEqual(data["historical_hash_only_identities"], 1)
            self.assertEqual(data["unique_candidate_urls"], 0)
            self.assertFalse(data["device_verified"])
            self.assertNotIn("Old Stream", summary.read_text(encoding="utf-8"))

    def test_full_playback_aggregate_read_without_url_fabrication(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "playback.json"
            digest = hashlib.sha256(b"old").hexdigest()
            src.write_text(json.dumps({"coverage_complete": True, "unique_tested": 1,
                "channel_results": [{"url_sha256": digest, "playback": "VIDEO_DECODED"}]}))
            rows = list(guard.read_historical_aggregate(src))
            self.assertEqual(len(rows), 1)
            protected, candidates, summary = guard.reconcile(rows, expected_historical_records=1)
            self.assertEqual(len(protected), 1)
            self.assertEqual(candidates, [])
            self.assertEqual(summary["historical_hash_only_identities"], 1)

    def test_incomplete_historical_aggregate_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "incomplete.json"
            for state in ({"coverage_complete": False, "unique_tested": 1, "channel_results": [{}]},
                          {"coverage_complete": True, "unique_tested": 2, "channel_results": [{}]}):
                src.write_text(json.dumps(state))
                with self.assertRaises(ValueError):
                    list(guard.read_historical_aggregate(src))


if __name__ == "__main__":
    unittest.main()
