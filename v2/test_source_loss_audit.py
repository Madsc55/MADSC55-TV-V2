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
    def test_threshold_rejected(self):
        with self.assertRaises(ValueError):
            compare(report(), report(), 1.2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
