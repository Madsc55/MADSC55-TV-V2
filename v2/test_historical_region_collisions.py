#!/usr/bin/env python3
"""Stage 3 grouped regressions for contradictory regional evidence and provenance."""
import hashlib
import unittest

from historical_inventory_guard import reconcile, classify


class HistoricalRegionCollisionTests(unittest.TestCase):
    def test_conflicting_same_url_tr_az_is_not_published_as_either(self):
        url = "https://fixture.example.org/public/live.m3u8"
        old = [
            {"url": url, "scope": "TR", "source": "#60-first", "name": "Channel"},
            {"url": url, "scope": "AZ", "source": "#60-second", "name": "Channel"},
            {"url_sha256": hashlib.sha256(b"unresolved").hexdigest(), "source": "#60"},
        ]
        current = [{"url": url, "scope": "TR", "source": "recent"}]
        raw, indexed, summary = reconcile(old, current, 3)
        self.assertEqual(raw[:3], old)
        self.assertEqual(len(indexed), 1)
        self.assertEqual(indexed[0]["region_candidate"], "UNKNOWN")
        self.assertEqual(indexed[0]["classification_evidence"], "CONFLICTING_TR_AZ_EVIDENCE")
        self.assertEqual(indexed[0]["source_ids"], ["#60-first", "#60-second", "recent"])
        self.assertEqual(summary["conflicting_tr_az_candidate_urls"], 1)
        self.assertEqual(summary["historical_hash_only_identities"], 1)
        self.assertEqual(summary["historical_records_preserved"], 3)
        self.assertFalse(indexed[0]["spoken_language_verified"])

    def test_current_evidence_conflict_does_not_erase_historical_label(self):
        url = "https://fixture.example.org/another.m3u8"
        old = [{"url": url, "country": "Türkiye", "source": "historical"}]
        current = [{"url": url, "country": "Azerbaijan", "source": "current"}]
        raw, indexed, summary = reconcile(old, current, 1)
        self.assertEqual(raw, old + current)
        self.assertEqual(indexed[0]["region_candidate"], "UNKNOWN")
        self.assertEqual(summary["conflicting_tr_az_candidate_urls"], 1)
        self.assertEqual(summary["historical_tr_candidate_records"], 1)
        self.assertEqual(summary["unique_candidate_urls"], 1)

    def test_matching_evidence_keeps_region_and_exact_url_dedup(self):
        url = "https://fixture.example.org/tv.m3u8?key=A"
        another = "https://fixture.example.org/tv.m3u8?key=B"
        old = [{"url": url, "tvg_id": "TRT1.tr"}, {"url": url, "scope": "TR"},
               {"url": another, "scope": "AZ"}]
        raw, indexed, summary = reconcile(old, [], 3)
        self.assertEqual(len(raw), 3)
        self.assertEqual(len(indexed), 2)
        self.assertEqual(summary["historical_duplicate_url_rows"], 1)
        self.assertEqual(summary["conflicting_tr_az_candidate_urls"], 0)
        self.assertEqual({x["region_candidate"] for x in indexed}, {"TR", "AZ"})
        self.assertEqual(len({x["url_sha256"] for x in indexed}), 2)

    def test_unknown_metadata_never_promotes_to_spoken_language(self):
        self.assertFalse(classify({"scope": "TR"})["spoken_language_verified"])
        self.assertEqual(classify({"name": "Global news"})["region_candidate"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
