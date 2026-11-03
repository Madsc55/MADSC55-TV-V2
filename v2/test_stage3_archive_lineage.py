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
    SCHEMA, SCHEMA_V2, digest, preserve_to_new_archive, reconcile,
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

    def test_same_hash_with_tampered_region_source_or_flags_is_rejected(self):
        old = [{"url_sha256": digest("https://fixture.example.org/real.m3u8"),
                "region_candidate": "TR", "source": "run60",
                "classification_evidence": "METADATA",
                "spoken_language_verified": False, "device_verified": False}]
        self.assertEqual(verify_historical_baseline(old, old),
                         hashlib.sha256(old[0]["url_sha256"].encode()).hexdigest())
        for patched in (
            dict(old[0], region_candidate="AZ"),
            dict(old[0], source="unknown"),
            dict(old[0], classification_evidence="SOURCE_GEO"),
            dict(old[0], device_verified=True),
            dict(old[0], spoken_language_verified=True),
        ):
            with self.subTest(patched=patched), self.assertRaisesRegex(
                    ValueError, "metadata differs"):
                verify_historical_baseline([patched], old)

    def test_metadata_integrity_is_order_independent_but_complete(self):
        first = {"url_sha256": hashlib.sha256(b"stage3-first").hexdigest(),
                 "source": "original"}
        second = {"url_sha256": hashlib.sha256(b"stage3-second").hexdigest(),
                  "source": "original-2"}
        self.assertEqual(verify_historical_baseline([first, second], [second, first]),
                         verify_historical_baseline([second, first], [first, second]))
        with self.assertRaisesRegex(ValueError, "metadata differs"):
            verify_historical_baseline([first, dict(second, status="INVENTED")],
                                       [first, second])

    def test_v2_manifest_detects_deletion_of_full_authenticated_tail_block(self):
        original = [{"url_sha256": hashlib.sha256(("real-history-%d" % n).encode()).hexdigest(),
                     "source": "#60", "region_candidate": "UNKNOWN",
                     "classification_evidence": "NONE"}
                    for n in range(205)]
        protected, view, _ = reconcile(original, [], 205)
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "real.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "3c" * 32}):
                self.assertTrue(preserve_to_new_archive(archive, protected, view))
                unmodified = restore(archive)
                self.assertEqual(unmodified[-1]["kind"], "archive_manifest")
                self.assertEqual(unmodified[-1]["guard_schema"], SCHEMA_V2)
                history, newer, candidates = unpack_archive_snapshot(unmodified, 205)
                self.assertEqual(history, original)
                self.assertEqual(newer, [])
                self.assertEqual(candidates, [])
                # All remaining blocks are valid AES-GCM plaintext, but their
                # authenticated manifest is absent: never accept this as done.
                with self.assertRaisesRegex(ValueError, "manifest missing"):
                    unpack_archive_snapshot(unmodified[:-1], 205)
                # A missing middle data block must fail, not merely report
                # fewer streams or regenerate a smaller candidate view.
                with self.assertRaisesRegex(ValueError, "block count"):
                    unpack_archive_snapshot(unmodified[:1] + unmodified[2:], 205)

    def test_v2_manifest_detects_reordered_blocks_or_missing_candidate_view(self):
        original = [{"url_sha256": hashlib.sha256(("original-%d" % n).encode()).hexdigest()}
                    for n in range(105)]
        new = [{"url": "https://fixture.example.org/extra.m3u8", "source": "later"}]
        protected, view, _ = reconcile(original, new, 105)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "complete.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
                self.assertTrue(preserve_to_new_archive(path, protected, view))
                blocks = restore(path)
                self.assertGreaterEqual(len(blocks), 4)
                with self.assertRaisesRegex(ValueError, "payload differs"):
                    unpack_archive_snapshot([blocks[1], blocks[0], *blocks[2:]], 105)
                # Removing a complete candidate block leaves old history intact
                # but must still be diagnosed as a loss of recent evidence.
                with self.assertRaisesRegex(ValueError, "block count"):
                    unpack_archive_snapshot(blocks[:-2] + blocks[-1:], 105)

    def test_failed_duplicate_and_sha_only_incoming_rows_survive_aesgcm_recovery(self):
        url = "https://fixture.example.org/already-seen.m3u8?key=ONE"
        historical = [
            {"url_sha256": digest(url), "source": "#60",
             "region_candidate": "TR", "classification_evidence": "METADATA"},
            {"url_sha256": hashlib.sha256(b"still-lost").hexdigest(),
             "source": "#60", "region_candidate": "UNKNOWN",
             "classification_evidence": "NONE"},
        ]
        incoming = [
            {"url": url, "name": "First", "source": "new-a", "scope": "TR"},
            {"url": url, "name": "Duplicate listing", "source": "new-b", "scope": "TR"},
            {"url": "http://127.0.0.1/internal", "status": "FAILED", "source": "failed"},
            {"url_sha256": hashlib.sha256(b"not-yet-recovered").hexdigest(),
             "source": "new-hash-only", "status": "PENDING"},
            {"anonymous_id": "no-address", "source": "unidentified"},
            {"url_sha256": digest(url), "source": "late-hash-provenance"},
        ]
        preserved, candidates, report = reconcile(historical, incoming, 2)
        self.assertEqual(preserved, historical + incoming)
        self.assertEqual(report["historical_records_preserved"], 2)
        self.assertEqual(report["current_records_preserved"], 6)
        self.assertEqual(report["current_invalid_records_preserved"], 4)
        self.assertEqual(report["current_duplicate_url_rows_preserved"], 1)
        self.assertEqual(report["total_raw_records_preserved"], 8)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_ids"],
                         ["#60", "new-a", "new-b", "late-hash-provenance"])
        self.assertEqual(candidates[0]["region_candidate"], "TR")
        self.assertEqual(report["historical_hash_only_linked_to_real_urls"], 1)
        self.assertEqual(report["unique_candidate_urls"], 1)
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "history-and-failures.enc"
            rerecorded = Path(tmp) / "history-and-failures-again.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "7c" * 32}):
                self.assertTrue(preserve_to_new_archive(archive, preserved, candidates))
                old, current, view = unpack_archive_snapshot(restore(archive), 2)
                self.assertEqual(old, historical)
                self.assertEqual(current, incoming)
                self.assertEqual(view, candidates)
                redone, recon_candidates, summary = reconcile(old, current, 2)
                self.assertEqual(redone, preserved)
                self.assertEqual(recon_candidates, candidates)
                self.assertTrue(preserve_to_new_archive(
                    rerecorded, redone, recon_candidates))
                self.assertEqual(restore(archive), restore(rerecorded))

    def test_valid_historical_url_and_duplicate_current_sources_all_preserved(self):
        url = "https://fixture.example.org/historic-live.m3u8"
        old = [{"url": url, "source": "old", "scope": "TR"}]
        now = [
            {"url": url, "source": "relisted", "scope": "TR"},
            {"url": url, "source": "relisted-second", "scope": "TR"},
            {"url_sha256": digest(url), "source": "metadata-only", "scope": "TR"},
        ]
        raw, view, counts = reconcile(old, now, 1)
        self.assertEqual(raw, old + now)
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]["source_ids"],
                         ["old", "relisted", "relisted-second", "metadata-only"])
        self.assertEqual(counts["historical_duplicate_identity_rows"], 0)
        self.assertEqual(counts["current_duplicate_url_rows"], 1)
        self.assertEqual(counts["current_records_preserved"], 3)
        self.assertEqual(counts["historical_unique_real_urls"], 1)

    def test_legacy_exact_count_archive_remains_compatible(self):
        old = [{"url_sha256": hashlib.sha256(b"old").hexdigest()}]
        self.assertEqual(unpack_archive_snapshot(old, 1), (old, [], None))
        with self.assertRaises(ValueError):
            unpack_archive_snapshot(old, 2)


if __name__ == "__main__":
    unittest.main()
