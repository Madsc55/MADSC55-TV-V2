"""Offline regression tests for authenticated, restartable real IPTV scan progress."""
import json
import tempfile
import time
import unittest
from pathlib import Path

from scan_checkpoint import (
    MAX_AGE_SECONDS, checkpoint_row, load_progress, save_progress,
)


class ScanCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        self.path = self.root / "ibo-scan-progress.enc"
        self.secret = "offline-checkpoint-passphrase-123"
        self.url = "https://example.org/live.m3u8?token=private-do-not-log"
        self.good = {
            "decoded_av_verified": True, "decode_status": "DECODED_AV",
            "verified_quality": {"av_verified": True, "quality": "HD"},
        }

    def test_encrypted_round_trip_and_atomic_checkpoint_replacement(self):
        original = checkpoint_row(
            self.url, self.good, {"last_http_status": 200})
        save_progress(self.path, self.secret, worldwide=True,
                      rows={self.url: original})
        sealed = self.path.read_bytes()
        self.assertNotIn(self.url.encode(), sealed)
        self.assertNotIn(b"private-do-not-log", sealed)
        rows = load_progress(self.path, self.secret, worldwide=True)
        self.assertEqual(rows[self.url]["url_sha256"], original["url_sha256"])
        self.assertTrue(rows[self.url]["result"]["decoded_av_verified"])
        self.assertEqual(rows[self.url]["checked_at"], original["checked_at"])
        # A later checkpoint replaces only the dedicated progress file.
        second_url = "https://example.org/failed.m3u8"
        second = checkpoint_row(
            second_url, None, {"last_http_status": 404})
        save_progress(self.path, self.secret, worldwide=True,
                      rows={self.url: original, second_url: second})
        rows = load_progress(self.path, self.secret, worldwide=True)
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[second_url]["result"])
        self.assertEqual(rows[second_url]["diagnostics"]["last_http_status"], 404)

    def test_stale_observations_do_not_renew_themselves(self):
        now = time.time()
        stale = checkpoint_row(
            self.url, self.good, {}, checked_at=now - MAX_AGE_SECONDS - 1)
        save_progress(self.path, self.secret, worldwide=True,
                      rows={self.url: stale})
        self.assertEqual(load_progress(
            self.path, self.secret, worldwide=True, now=now), {})

    def test_corruption_wrong_secret_and_scope_are_refused(self):
        row = checkpoint_row(self.url, self.good, {})
        save_progress(self.path, self.secret, worldwide=True,
                      rows={self.url: row})
        with self.assertRaises(ValueError):
            load_progress(self.path, self.secret, worldwide=False)
        with self.assertRaises(Exception):
            load_progress(self.path, "not-the-correct-password", worldwide=True)
        damaged = bytearray(self.path.read_bytes())
        damaged[-1] ^= 1
        self.path.write_bytes(damaged)
        with self.assertRaises(Exception):
            load_progress(self.path, self.secret, worldwide=True)

    def test_url_identity_and_av_evidence_cannot_be_forged(self):
        with self.assertRaises(ValueError):
            checkpoint_row(self.url, {
                "decoded_av_verified": True,
                "decode_status": "NO_DECODED_AUDIO",
                "verified_quality": {"av_verified": False},
            }, {})
        row = checkpoint_row(self.url, self.good, {})
        row["url_sha256"] = "0" * 64
        save_progress(self.path, self.secret, worldwide=True,
                      rows={self.url: row})
        with self.assertRaises(ValueError):
            load_progress(self.path, self.secret, worldwide=True)

    def test_missing_progress_falls_back_to_new_scan_and_protected_baseline_stays(self):
        self.assertEqual(load_progress(
            self.path, self.secret, worldwide=True), {})
        baseline = self.root / "ibo-candidate-inventory.jsonl.enc"
        baseline.write_bytes(b"DO_NOT_TOUCH")
        row = checkpoint_row(self.url, self.good, {})
        save_progress(self.path, self.secret, worldwide=True,
                      rows={self.url: row})
        self.assertEqual(baseline.read_bytes(), b"DO_NOT_TOUCH")
        with self.assertRaises(ValueError):
            save_progress(baseline, self.secret, worldwide=True,
                          rows={self.url: row})

    def test_symlinked_checkpoint_is_refused(self):
        target = self.root / "protected.m3u8"
        target.write_bytes(b"PROTECTED_M3U")
        self.path.symlink_to(target)
        row = checkpoint_row(self.url, self.good, {})
        with self.assertRaises(ValueError):
            save_progress(self.path, self.secret, worldwide=True,
                          rows={self.url: row})
        with self.assertRaises(ValueError):
            load_progress(self.path, self.secret, worldwide=True)
        self.assertEqual(target.read_bytes(), b"PROTECTED_M3U")


if __name__ == "__main__":
    unittest.main()
