#!/usr/bin/env python3
"""Source loss audit fixtures; no network and no playlist mutation."""
import unittest
from source_loss_audit import compare

def report(*rows):
    return {"source_audit": [{"source": name, "status": status, "distinct_stream_urls": count}
                             for name, status, count in rows]}

class SourceLossTests(unittest.TestCase):
    def test_historical_large_source_drop(self):
        before = report(("iptv-org", "PARSED_NOT_PLAYBACK_VERIFIED", 11204),
                        ("free-tv", "PARSED_NOT_PLAYBACK_VERIFIED", 1347))
        after = report(("iptv-org", "PARSED_NOT_PLAYBACK_VERIFIED", 9),
                       ("free-tv", "PARSED_NOT_PLAYBACK_VERIFIED", 5))
        self.assertEqual([x["reason"] for x in compare(before, after)["findings"]],
                         ["SOURCE_DROP", "SOURCE_DROP"])

    def test_missing_and_failed_not_silenced(self):
        before = report(("old", "PARSED_NOT_PLAYBACK_VERIFIED", 100),
                        ("failed", "PARSED_NOT_PLAYBACK_VERIFIED", 30))
        after = report(("failed", "FETCH_FAILED", 0))
        self.assertEqual([x["reason"] for x in compare(before, after)["findings"]],
                         ["FETCH_FAILED", "SOURCE_MISSING"])

    def test_normal_change(self):
        before = report(("a", "PARSED_NOT_PLAYBACK_VERIFIED", 100))
        after = report(("a", "PARSED_NOT_PLAYBACK_VERIFIED", 70))
        self.assertEqual(compare(before, after)["status"], "NO_LARGE_REGRESSION")

    def test_duplicate_source_rejected(self):
        with self.assertRaises(ValueError):
            compare(report(("a", "ok", 10), ("a", "ok", 20)), report())

    def test_invalid_previous_count_rejected(self):
        with self.assertRaises(ValueError):
            compare(report(("a", "ok", -1)), report())

    def test_invalid_current_count_rejected(self):
        with self.assertRaises(ValueError):
            compare(report(("a", "ok", 10)), report(("a", "ok", True)))

    def test_missing_previous_audit_is_not_success(self):
        result = compare(report(), report(("new", "ok", 20)))
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["findings"][0]["reason"], "MISSING_SOURCE_AUDIT")
    def test_missing_current_audit_is_not_success(self):
        result = compare(report(("old", "ok", 20)), report())
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["findings"][0]["reason"], "MISSING_SOURCE_AUDIT")
    def test_same_count_but_missing_historical_sha_is_flagged(self):
        import hashlib
        digest = lambda s: hashlib.sha256(s.encode()).hexdigest()
        before = report(("tr", "PARSED_NOT_PLAYBACK_VERIFIED", 2))
        after = report(("tr", "PARSED_NOT_PLAYBACK_VERIFIED", 2))
        before["candidates"] = [{"url_sha256": digest("old-a")},
                                {"url_sha256": digest("old-b")}]
        after["candidates"] = [{"url_sha256": digest("old-a")},
                               {"url_sha256": digest("new-c")}]
        result = compare(before, after)
        self.assertEqual(result["candidate_audit"]["absent_from_current_candidates"], 1)
        self.assertEqual(result["findings"][0]["reason"], "HISTORICAL_CANDIDATES_ABSENT")

    def test_truncated_inventory_cannot_prove_absence(self):
        before = report(("tr", "PARSED_NOT_PLAYBACK_VERIFIED", 2))
        after = report(("tr", "PARSED_NOT_PLAYBACK_VERIFIED", 2))
        before["candidates"] = []
        after["candidates"] = []
        after["candidates_truncated"] = True
        self.assertEqual(compare(before, after)["candidate_audit"]["status"], "NOT_COMPARABLE")

    def test_invalid_candidate_hash_or_duplicate_rejected(self):
        import hashlib
        d = hashlib.sha256(b"real").hexdigest()
        before = report(("tr", "ok", 1))
        after = report(("tr", "ok", 1))
        before["candidates"] = [{"url_sha256": d}, {"url_sha256": d}]
        after["candidates"] = []
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compare(before, after)
        before["candidates"] = [{"url_sha256": "not-a-hash"}]
        with self.assertRaisesRegex(ValueError, "Invalid candidate"):
            compare(before, after)

    def test_threshold_rejected(self):
        with self.assertRaises(ValueError):
            compare(report(), report(), 1.2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
