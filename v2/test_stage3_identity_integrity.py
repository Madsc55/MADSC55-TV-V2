#!/usr/bin/env python3
"""Grouped Stage 3 URL/hash integrity and conservative TR/AZ classification."""
import hashlib
import unittest

from historical_inventory_guard import digest, identity, reconcile, region_signals


class Stage3IdentityIntegrityTests(unittest.TestCase):
    def test_valid_url_with_conflicting_sha_is_rejected_before_dedup(self):
        url = "https://fixture.example.org/channel.m3u8?key=ORIGINAL"
        false_digest = digest("https://fixture.example.org/channel.m3u8?key=OTHER")
        corrupted = {"url": url, "url_sha256": false_digest, "source": "historic"}
        self.assertNotEqual(digest(url), false_digest)
        with self.assertRaisesRegex(ValueError, "disagree"):
            identity(corrupted)
        with self.assertRaisesRegex(ValueError, "disagree"):
            reconcile([corrupted], expected_historical_records=1)
        with self.assertRaisesRegex(ValueError, "disagree"):
            reconcile([{"url_sha256": digest(url)}], [corrupted], 1)

    def test_matching_legacy_url_hash_is_accepted(self):
        url = "https://fixture.example.org/valid.m3u8?token=ONE"
        row = {"url": url, "url_sha256": digest(url).upper(), "scope": "TR"}
        self.assertEqual(identity(row), digest(url))
        preserved, indexed, counts = reconcile([row], [], 1)
        self.assertEqual(preserved, [row])
        self.assertEqual(len(indexed), 1)
        self.assertEqual(indexed[0]["region_candidate"], "TR")
        self.assertEqual(counts["historical_unique_identities"], 1)

    def test_same_record_geo_tr_and_tvg_az_cannot_be_published_as_tr(self):
        url = "https://fixture.example.org/same-stream.m3u8"
        row = {"url": url, "country": "Türkiye", "tvg_id": "News.az"}
        self.assertEqual(region_signals(row), {"TR", "AZ"})
        protected, indexed, report = reconcile([row], [], 1)
        self.assertEqual(protected, [row])
        self.assertEqual(indexed[0]["region_candidate"], "UNKNOWN")
        self.assertEqual(indexed[0]["classification_evidence"],
                         "CONFLICTING_TR_AZ_EVIDENCE")
        self.assertEqual(report["conflicting_tr_az_candidate_urls"], 1)
        self.assertEqual(report["historical_rows_with_internal_region_conflict"], 1)
        self.assertFalse(indexed[0]["spoken_language_verified"])

    def test_conflicting_country_hints_on_sha_only_record_are_retained(self):
        url = "https://fixture.example.org/recovered.m3u8"
        old = [{"url_sha256": digest(url), "scope": "TR",
                "tvg_id": "News.az", "source": "run60"}]
        now = [{"url": url, "source": "backup"}]
        raw, indexed, report = reconcile(old, now, 1)
        self.assertEqual(raw[:1], old)
        self.assertEqual(indexed[0]["region_candidate"], "UNKNOWN")
        self.assertEqual(indexed[0]["source_ids"], ["run60", "backup"])
        self.assertEqual(report["historical_hash_only_linked_to_real_urls"], 1)
        self.assertEqual(report["historical_rows_with_internal_region_conflict"], 1)

    def test_same_url_with_different_token_is_not_a_duplicate(self):
        urls = ["https://fixture.example.org/live.m3u8?token=A",
                "https://fixture.example.org/live.m3u8?token=B"]
        old = [{"url": value, "tvg_id": "Channel.tr"} for value in urls]
        _, indexed, report = reconcile(old, [], 2)
        self.assertEqual(len(indexed), 2)
        self.assertEqual(report["historical_duplicate_identity_rows"], 0)
        self.assertEqual(report["conflicting_tr_az_candidate_urls"], 0)


if __name__ == "__main__":
    unittest.main()
