"""Offline fail-closed checks for Stage C evidence validator."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("verify_stage_c_evidence.py")

class StageCEvidenceTests(unittest.TestCase):
    def test_missing_evidence_fails_without_state_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            result = subprocess.run([sys.executable, str(SCRIPT), "--evidence-dir", str(root)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["passed"])
            self.assertFalse(payload["checks"]["device"]["passed"])
            self.assertFalse(payload["checks"]["restore"]["passed"])
            self.assertEqual(list(root.iterdir()), [])

    def test_mock_and_unverified_media_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / "device.json").write_text(json.dumps({
                "passed": True, "environment": "physical_android", "mock": True,
                "device_id": "test", "player_version": "test",
                "started_at": "start", "finished_at": "finish",
                "sessions": [{"channel_id": "x", "video_ok": True, "audio_ok": False,
                              "same_session": True}]
            }))
            (root / "restore.json").write_text(json.dumps({
                "passed": True, "environment": "independent_isolated", "mock": True,
                "source_archive_sha256": "0" * 64,
                "archive_integrity_passed": True, "decryption_passed": True,
                "source_count": 1, "restored_count": 1, "missing_count": 0,
                "corrupt_count": 0, "duplicate_count": 0,
                "started_at": "start", "finished_at": "finish"
            }))
            result = subprocess.run([sys.executable, str(SCRIPT), "--evidence-dir", str(root)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)["passed"])

if __name__ == "__main__":
    unittest.main()
