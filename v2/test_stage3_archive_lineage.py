#!/usr/bin/env python3
"""Grouped Stage 3 encrypted archive lineage and immutable baseline regressions."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from encrypted_archive import restore
from historical_inventory_guard import (
    SCHEMA, digest, preserve_to_new_archive, reconcile,
    unpack_archive_snapshot, verify_historical_baseline,
)


class Stage3ArchiveLineageTests(unittest.TestCase):
    def test_recover_preserved_history_and_matched_url_as_separate_groups(self):
        url = "https://fixture.example.org/old.m3u8?token=REAL"
        original = [
            {"url_sha256": digest(url), "source": "historic", "region_candidate": "TR",
             "classification_evidence": "METADATA"},
            {"url_sha256": hashlib.sha256(b"not-found").hexdigest(), "source": "historic"},
        ]
        new = [{"url": url, "source": "later-archive"}]
        protected, candidates, counts = reconcile(original, new, 2)
        self.assertEqual(len(protected), 3)
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first.enc"
            second = Path(temp) / "second.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "8a" * 32}):
                self.assertTrue(preserve_to_new_archive(first, protected, candidates))
                recovered_history, recovered_new, recovered_view = unpack_archive_snapshot(
                    restore(first), 2)
                self.assertEqual(recovered_history, original)
                self.assertEqual(recovered_new, new)
                self.assertEqual(recovered_view, candidates)
                next_protected, next_candidates, next_summary = reconcile(
                    recovered_history, recovered_new, 2)
                self.assertEqual(next_protected, protected)
                self.assertEqual(next_candidates, candidates)
                self.assertEqual(next_summary["historical_hash_only_linked_to_real_urls"], 1)
                self.assertTrue(preserve_to_new_archive(second, next_protected, next_candidates))
                self.assertEqual(restore(first), restore(second))

    def test_archive_blocks_mixed_or_reordered_fail_closed(self):
        a = {"kind": "raw_historical_and_new", "guard_schema": SCHEMA,
             "records": [{"url_sha256": hashlib.sha256(b"1").hexdigest()}]}
        b = {"kind": "deduplicated_view", "guard_schema": SCHEMA,
             "records": [{"url": "https://fixture.example.org/a.m3u8"}]}
        with self.assertRaisesRegex(ValueError, "follows candidate"):
            unpack_archive_snapshot([b, a], 1)
        with self.assertRaisesRegex(ValueError, "Mixed"):
            unpack_archive_snapshot([a, {"url": "https://fixture.example.org/b.m3u8"}], 1)
        with self.assertRaisesRegex(ValueError, "shorter"):
            unpack_archive_snapshot([a], 2)
        with self.assertRaisesRegex(ValueError, "block fields"):
            unpack_archive_snapshot([dict(a, unexpected=True)], 1)

    def test_baseline_identity_membership_not_only_count(self):
        a = {"url_sha256": hashlib.sha256(b"record-a").hexdigest()}
        b = {"url_sha256": hashlib.sha256(b"record-b").hexdigest()}
        c = {"url_sha256": hashlib.sha256(b"record-c").hexdigest()}
        digest = verify_historical_baseline([b, a], [a, b])
        self.assertEqual(len(digest), 64)
        with self.assertRaisesRegex(ValueError, "immutable baseline"):
            verify_historical_baseline([a, c], [a, b])
        with self.assertRaisesRegex(ValueError, "immutable baseline"):
            verify_historical_baseline([a, a], [a, b])

    def test_legacy_exact_count_archive_remains_compatible(self):
        old = [{"url_sha256": hashlib.sha256(b"old").hexdigest()}]
        self.assertEqual(unpack_archive_snapshot(old, 1), (old, [], None))
        with self.assertRaises(ValueError):
            unpack_archive_snapshot(old, 2)


if __name__ == "__main__":
    unittest.main()
