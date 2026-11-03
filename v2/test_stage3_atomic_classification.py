#!/usr/bin/env python3
"""Stage 3 grouped fail-closed archive publication and TR/AZ evidence tests."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from historical_inventory_guard import classify, digest, preserve_to_new_archive, reconcile
from encrypted_archive import restore


class Stage3AtomicClassificationTests(unittest.TestCase):
    def test_internal_tr_az_conflict_is_unknown_even_in_raw_history_counts(self):
        url = "https://fixture.example.org/mixed.m3u8"
        record = {"url": url, "scope": "TR", "tvg_id": "News.az", "source": "#60"}
        self.assertEqual(classify(record)["region_candidate"], "UNKNOWN")
        self.assertEqual(classify(record)["classification_evidence"],
                         "CONFLICTING_TR_AZ_EVIDENCE")
        raw, indexed, report = reconcile([record], [], 1)
        self.assertEqual(raw, [record])
        self.assertEqual(report["historical_unknown_region_records"], 1)
        self.assertEqual(report["historical_tr_candidate_records"], 0)
        self.assertEqual(report["historical_rows_with_internal_region_conflict"], 1)
        self.assertEqual(indexed[0]["region_candidate"], "UNKNOWN")

    def test_reviewed_hash_only_conflict_is_not_repromoted(self):
        url = "https://fixture.example.org/reviewed.m3u8"
        old = {"url_sha256": digest(url), "region_candidate": "UNKNOWN",
               "classification_evidence": "CONFLICTING_TR_AZ_EVIDENCE",
               "scope": "TR", "source": "#60"}
        self.assertEqual(classify(old)["region_candidate"], "UNKNOWN")
        _, indexed, report = reconcile([old], [{"url": url, "scope": "TR"}], 1)
        self.assertEqual(indexed[0]["region_candidate"], "UNKNOWN")
        self.assertEqual(report["historical_unknown_region_records"], 1)

    def test_failed_encryption_leaves_no_partial_final_archive(self):
        historical = [{"url_sha256": hashlib.sha256(b"real-history").hexdigest()}]
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "historic.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "cd" * 32}):
                with patch("historical_inventory_guard.append",
                           side_effect=RuntimeError("simulated broken append")):
                    with self.assertRaisesRegex(RuntimeError, "broken append"):
                        preserve_to_new_archive(dest, historical, [])
                self.assertFalse(dest.exists())
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_destination_is_never_overwritten_during_publication(self):
        historical = [{"url_sha256": hashlib.sha256(b"real-history").hexdigest()}]
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "historic.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "e2" * 32}):
                # Destination appears *after* the initial existence check.
                # The atomic os.link must reject it, preserving the evidence.
                def race_create(_src, _dst, **_kwargs):
                    dest.write_bytes(b"existing evidence, no overwrite")
                    raise FileExistsError("simulated concurrent archive writer")
                with patch("historical_inventory_guard.os.link", side_effect=race_create):
                    with self.assertRaises(FileExistsError):
                        preserve_to_new_archive(dest, historical, [])
                self.assertEqual(dest.read_bytes(), b"existing evidence, no overwrite")
                self.assertEqual([p.name for p in Path(directory).iterdir()],
                                 ["historic.enc"])

    def test_successful_private_archive_has_manifest_and_is_verifiable(self):
        historical = [{"url_sha256": hashlib.sha256(b"real-history").hexdigest()}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "historic.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ad" * 32}):
                self.assertTrue(preserve_to_new_archive(path, historical, []))
                self.assertEqual(restore(path)[-1]["kind"], "archive_manifest")
                self.assertEqual(path.stat().st_mode & 0o077, 0)
                self.assertEqual([p.name for p in Path(directory).iterdir()],
                                 ["historic.enc"])


if __name__ == "__main__":
    unittest.main()
