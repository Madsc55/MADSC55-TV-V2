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

    def test_bootstrap_real_pending_inventory_from_pre_checkpoint_run(self):
        """Preserve all tested records without calling FFmpeg or upgrading old proof."""
        from datetime import datetime, timezone
        from scan_checkpoint import bootstrap_from_pending_inventory
        from secure_archive import encrypt
        from stage3_identity_recovery import url_sha256

        pending = self.root / "ibo-candidate-inventory.jsonl.pending.enc"
        report = self.root / "ibo-real-scan-report.json"
        failed_url = "https://example.org/failed.m3u8"
        rows = [
            {"url": self.url, "url_sha256": url_sha256(self.url),
             "http_hls_status": "AV_VERIFIED", "decoded_av_verified": True,
             "decode_status": "DECODED_AV", "verified_quality": self.good["verified_quality"],
             "last_http_status": 200, "last_timeout": False},
            {"url": failed_url, "url_sha256": url_sha256(failed_url),
             "http_hls_status": "UNVERIFIED_OR_FAILED", "decoded_av_verified": False,
             "decode_status": "NOT_DECODED_THIS_RUN",
             "last_http_status": 999, "last_timeout": False},
        ]
        payload = "".join(json.dumps(x) + "\n" for x in rows).encode()
        pending.write_bytes(encrypt(payload, self.secret))
        report_data = {
            "status": "INCOMPLETE_SOURCE_FETCH_OR_DROP",
            "scan_scope": "WORLDWIDE_ALL_SOURCE_ENTRIES",
            "archive_restore_test_passed": True, "mock_data_used": False,
            "candidate_inventory": "/runner/v2/reports/ibo-candidate-inventory.jsonl.pending.enc",
            "unique_new_candidates": 2, "http_checked": 2,
            "av_verified": 1, "failed_sources": [{"id": "bad-feed"}],
        }
        report.write_text(json.dumps(report_data))
        started = datetime.now(timezone.utc).isoformat()
        result = bootstrap_from_pending_inventory(
            pending, report, self.path, self.secret, observed_at=started)
        self.assertEqual(result["resumed_rows"], 2)
        self.assertEqual(result["prior_decoded_av"], 1)
        self.assertTrue(result["last_scan_was_incomplete"])
        saved = load_progress(self.path, self.secret, worldwide=True)
        self.assertEqual(len(saved), 2)
        self.assertTrue(saved[self.url]["result"]["decoded_av_verified"])
        self.assertIsNone(saved[failed_url]["result"])
        # A report claiming unobserved success must never become a checkpoint.
        report_data["av_verified"] = 2
        report.write_text(json.dumps(report_data))
        with self.assertRaises(ValueError):
            bootstrap_from_pending_inventory(
                pending, report, self.path, self.secret, observed_at=started)
        self.assertEqual(len(load_progress(self.path, self.secret, worldwide=True)), 2)
        # Observations without a current-run decode may never be promoted.
        rows[0]["decoded_av_verified"] = False
        report_data["av_verified"] = 1
        report.write_text(json.dumps(report_data))
        pending.write_bytes(encrypt(
            "".join(json.dumps(x) + "\n" for x in rows).encode(), self.secret))
        with self.assertRaises(ValueError):
            bootstrap_from_pending_inventory(
                pending, report, self.path, self.secret, observed_at=started)
        self.assertEqual(len(load_progress(self.path, self.secret, worldwide=True)), 2)

    def test_bootstrap_rejects_expired_prior_run(self):
        from datetime import datetime, timezone
        from scan_checkpoint import bootstrap_from_pending_inventory
        with self.assertRaises(ValueError):
            bootstrap_from_pending_inventory(
                self.root / "ibo-candidate-inventory.jsonl.pending.enc",
                self.root / "ibo-real-scan-report.json", self.path,
                self.secret, observed_at="2026-01-01T00:00:00Z",
                now=datetime(2026, 2, 1, tzinfo=timezone.utc).timestamp())

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
