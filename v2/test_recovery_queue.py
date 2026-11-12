"""Offline recovery queue acceptance: no network or playlist mutation."""
import unittest
from recovery_queue import build_queue, sha_for_url


class RecoveryQueueTests(unittest.TestCase):
    def test_transient_retries_are_bounded(self):
        digest = sha_for_url("https://example.invalid/live")
        row = {"url_sha256": digest, "status": "TIMEOUT", "attempts": 1}
        self.assertEqual(build_queue([row], 3)["retry"][0]["next_attempt"], 2)
        self.assertEqual(len(build_queue([{**row, "attempts": 3}], 3)["hold"]), 1)

    def test_no_av_proof_never_accepted(self):
        digest = sha_for_url("https://example.invalid/live")
        for row in (
            {"url_sha256": digest, "status": "AV_VERIFIED", "video": True, "audio": False},
            {"url_sha256": digest, "status": "AV_VERIFIED", "video": True},
            {"url_sha256": digest, "status": "HTTP_200", "video": True, "audio": True},
        ):
            with self.subTest(row=row):
                self.assertEqual(build_queue([row])["verified"], [])

    def test_both_media_streams_required(self):
        row = {"url_sha256": sha_for_url("https://example.invalid/live"),
               "status": "AV_VERIFIED", "video": True, "audio": True}
        self.assertEqual(len(build_queue([row])["verified"]), 1)

    def test_url_digest_mismatch_is_rejected(self):
        row = {"url": "https://example.invalid/actual",
               "url_sha256": sha_for_url("https://example.invalid/other"),
               "status": "TIMEOUT"}
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            build_queue([row])

    def test_duplicate_and_invalid_digests_rejected(self):
        row = {"url_sha256": sha_for_url("https://example.invalid/live")}
        with self.assertRaises(ValueError):
            build_queue([row, row])
        with self.assertRaises(ValueError):
            build_queue([{"url_sha256": "wrong"}])
        with self.assertRaises(ValueError):
            build_queue([{**row, "attempts": -1}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
