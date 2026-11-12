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

    def test_transient_failures_are_not_accepted_as_empty_sources(self):
        previous = report(("a", "PARSED_NOT_PLAYBACK_VERIFIED", 100))
        for status in ("TIMEOUT", "RATE_LIMITED", "HTTP_ERROR", "PARSE_FAILED"):
            with self.subTest(status=status):
                current = report(("a", status, 0))
                finding = compare(previous, current)["findings"][0]
                self.assertEqual(finding["reason"], "SOURCE_UNAVAILABLE")
                self.assertEqual(finding["source_status"], status)
                self.assertIsNone(finding["current"])

    def test_source_drop_at_boundary(self):
        before = report(("a", "PARSED_NOT_PLAYBACK_VERIFIED", 100))
        exact_half = report(("a", "PARSED_NOT_PLAYBACK_VERIFIED", 50))
        below_half = report(("a", "PARSED_NOT_PLAYBACK_VERIFIED", 49))
        self.assertEqual(compare(before, exact_half)["status"], "NO_LARGE_REGRESSION")
        self.assertEqual(compare(before, below_half)["findings"][0]["reason"], "SOURCE_DROP")

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

    def test_threshold_rejected(self):
        with self.assertRaises(ValueError):
            compare(report(), report(), 1.2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
