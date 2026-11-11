"""Offline regression tests for the Stage 3 decision core."""
import hashlib
import unittest

from stage3_identity_recovery import (
    classify_failure, merge_evidence, recovery_decision, url_sha256,
)


class Stage3IdentityTests(unittest.TestCase):
    def test_exact_url_hash_including_token(self):
        a = "https://example.org/live.m3u8?token=a"
        b = "https://example.org/live.m3u8?token=b"
        self.assertEqual(url_sha256(a), hashlib.sha256(a.encode()).hexdigest())
        self.assertNotEqual(url_sha256(a), url_sha256(b))

    def test_bad_url_rejected(self):
        for url in ("file:///tmp/a", "https://user:pass@example.org/x", "/relative"):
            with self.assertRaises(ValueError):
                url_sha256(url)

    def test_transient_failures_preserve_inventory(self):
        record = {"url": "https://example.org/live.m3u8"}
        for status in (None, 408, 429, 500, 502, 503, 504):
            decision = recovery_decision(record, status)
            self.assertEqual(decision["action"], "RETRY")
            self.assertTrue(decision["preserve_history"])
            self.assertFalse(decision["remove_from_inventory"])
            self.assertFalse(decision["av_verified"])

    def test_http_success_not_av_proof(self):
        self.assertEqual(classify_failure(200), "CHECK_AV")
        self.assertEqual(classify_failure(404), "REVIEW")

    def test_merge_keeps_history_and_source_ids(self):
        url = "https://example.org/live.m3u8"
        old = {"url": url, "source_id": "legacy", "name": "TR channel",
               "observations": [{"status": "AV_VERIFIED"}]}
        new = {"url": url, "source_ids": ["new"], "name": "",
               "observations": [{"status": "TIMEOUT"}]}
        merged = merge_evidence(old, new)
        self.assertEqual(merged["source_ids"], ["legacy", "new"])
        self.assertEqual(len(merged["observations"]), 2)
        self.assertEqual(merged["name"], "TR channel")

    def test_no_cross_url_merge(self):
        with self.assertRaises(ValueError):
            merge_evidence({"url": "https://example.org/a"}, {"url": "https://example.org/b"})


if __name__ == "__main__":
    unittest.main()
