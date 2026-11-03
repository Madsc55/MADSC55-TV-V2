#!/usr/bin/env python3
"""Stage 3 hash-only identity reconciliation, evidence conflicts and provenance."""
import hashlib
import unittest
from historical_inventory_guard import reconcile, digest


class Stage3HashEvidenceLinkageTests(unittest.TestCase):
    def test_real_url_match_preserves_original_hash_only_source_provenance(self):
        url = "https://fixture.example.org/legitimate.m3u8?token=ONE"
        old = [
            {"url_sha256": digest(url), "source": "run60", "source_ids": ["historic-a"],
             "region_candidate": "TR", "classification_evidence": "METADATA"},
            {"url_sha256": digest(url), "source": "run60-backup",
             "region_candidate": "TR", "classification_evidence": "SOURCE_GEO"},
        ]
        now = [{"url": url, "source": "local-archive", "name": "News"}]
        protected, view, counts = reconcile(old, now, expected_historical_records=2)
        self.assertEqual(protected[:2], old)
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]["source_ids"],
                         ["historic-a", "run60", "run60-backup", "local-archive"])
        self.assertEqual(view[0]["region_candidate"], "TR")
        self.assertEqual(view[0]["classification_evidence"], "HISTORICAL_REGION_EVIDENCE")
        self.assertTrue(view[0]["historical_not_reverified"])
        self.assertFalse(view[0]["spoken_language_verified"])
        self.assertFalse(view[0]["device_verified"])
        self.assertEqual(counts["historical_duplicate_identity_rows"], 1)
        self.assertEqual(counts["historical_hash_only_linked_to_real_urls"], 1)
        self.assertEqual(counts["historical_hash_only_provenance_linked"], 1)

    def test_hash_only_tr_vs_new_az_is_conflict_not_silent_promotion(self):
        url = "https://fixture.example.org/az.m3u8"
        old = [{"url_sha256": digest(url), "source": "run60",
                "region_candidate": "TR", "classification_evidence": "METADATA"}]
        now = [{"url": url, "source": "today", "scope": "AZ"}]
        raw, view, counts = reconcile(old, now, 1)
        self.assertEqual(raw[0], old[0])
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]["source_ids"], ["run60", "today"])
        self.assertEqual(view[0]["region_candidate"], "UNKNOWN")
        self.assertEqual(view[0]["classification_evidence"], "CONFLICTING_TR_AZ_EVIDENCE")
        self.assertEqual(counts["conflicting_tr_az_candidate_urls"], 1)

    def test_two_conflicting_hash_only_rows_do_not_pick_current_tr(self):
        url = "https://fixture.example.org/conflict.m3u8"
        old = [{"url_sha256": digest(url), "region_candidate": region,
                "classification_evidence": "METADATA", "source": source}
               for region, source in (("TR", "old-tr"), ("AZ", "old-az"))]
        raw, view, result = reconcile(old, [{"url": url, "scope": "TR"}], 2)
        self.assertEqual(raw[:2], old)
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]["region_candidate"], "UNKNOWN")
        self.assertEqual(result["conflicting_tr_az_candidate_urls"], 1)
        self.assertEqual(result["historical_duplicate_identity_rows"], 1)
        self.assertEqual(result["historical_unique_identities"], 1)

    def test_prior_conflict_marker_cannot_be_overridden_by_new_source(self):
        url = "https://fixture.example.org/prior.m3u8"
        old = [{"url_sha256": digest(url), "region_candidate": "UNKNOWN",
                "classification_evidence": "CONFLICTING_TR_AZ_EVIDENCE"}]
        _, view, summary = reconcile(old, [{"url": url, "scope": "TR"}], 1)
        self.assertEqual(view[0]["region_candidate"], "UNKNOWN")
        self.assertEqual(view[0]["classification_evidence"], "CONFLICTING_TR_AZ_EVIDENCE")
        self.assertEqual(summary["conflicting_tr_az_candidate_urls"], 1)

    def test_unmatched_hash_only_history_does_not_create_url(self):
        old = [{"url_sha256": hashlib.sha256(b"not-a-real-url").hexdigest(),
                "source": "run60", "region_candidate": "AZ",
                "classification_evidence": "METADATA"}]
        raw, view, summary = reconcile(old, [], 1)
        self.assertEqual(raw, old)
        self.assertEqual(view, [])
        self.assertEqual(summary["historical_unique_identities"], 1)
        self.assertEqual(summary["historical_unique_real_urls"], 0)
        self.assertEqual(summary["historical_hash_only_provenance_linked"], 0)


if __name__ == "__main__":
    unittest.main()
