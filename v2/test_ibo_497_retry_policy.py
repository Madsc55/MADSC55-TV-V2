#!/usr/bin/env python3
"""Offline #497 retry policy regressions; no live network."""
import unittest
from v2.ibo_497_retry_policy import decide, TRANSIENT, SECURITY

class RetryPolicyTests(unittest.TestCase):
    def test_default_hold_all(self):
        for status in TRANSIENT | SECURITY | {"AV_VERIFIED", "UNKNOWN"}:
            self.assertEqual(decide(status, 1).action, "SECURITY_HOLD")
    def test_partial_acceptance_never_releases(self):
        for flags in [(True, False, True), (True, True, False), (False, True, True)]:
            self.assertEqual(decide("TIMEOUT", 1, sandbox_accepted=flags[0],
                                    hls_children_isolated=flags[1],
                                    final_test_authorized=flags[2]).action, "SECURITY_HOLD")
    def test_security_never_retried(self):
        for status in SECURITY | {"UNKNOWN", "AV_VERIFIED"}:
            self.assertEqual(decide(status, 1, sandbox_accepted=True,
                                    hls_children_isolated=True,
                                    final_test_authorized=True).action, "NO_RETRY")
    def test_bounded_transient_plan(self):
        expected = [(0, 30), (1, 30), (2, 60)]
        for count, delay in expected:
            result = decide("TIMEOUT", count, sandbox_accepted=True,
                            hls_children_isolated=True, final_test_authorized=True)
            self.assertEqual((result.action, result.delay_seconds), ("SCHEDULE_ONLY", delay))
            self.assertFalse(result.live_retry_authorized)
        self.assertEqual(decide("TIMEOUT", 3, sandbox_accepted=True,
                         hls_children_isolated=True, final_test_authorized=True).action, "EXHAUSTED")
    def test_bad_count_rejected(self):
        for count in (-1, 4, True, 1.5):
            with self.assertRaises(ValueError):
                decide("TIMEOUT", count)

if __name__ == "__main__":
    unittest.main()
