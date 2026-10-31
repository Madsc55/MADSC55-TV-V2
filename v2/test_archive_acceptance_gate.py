#!/usr/bin/env python3
"""Offline archive gate tests: absent, incomplete, and valid evidence."""
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from archive_acceptance_gate import check

class ArchiveGateTests(unittest.TestCase):
    def test_no_approval(self):
        with self.assertRaises(RuntimeError):
            check({})
    def test_approval_without_evidence(self):
        with self.assertRaises(RuntimeError):
            check({"V2_ARCHIVE_RESTORE_APPROVED": "true"})
    def test_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps({"encrypted": True, "durable": True}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                check({"V2_ARCHIVE_RESTORE_APPROVED": "true", "V2_ARCHIVE_RESTORE_EVIDENCE": str(path)})
    def evidence(self, directory, digest=None):
        restored = Path(directory) / "restored.bin"
        restored.write_bytes(b"test-only-restored-archive")
        actual = hashlib.sha256(restored.read_bytes()).hexdigest()
        path = Path(directory) / "evidence.json"
        record = {"encrypted": True, "durable": True,
                  "restore_test_passed": True, "integrity_verified": True,
                  "backup_location": "secure-store",
                  "restore_sha256": digest or actual, "restored_file": str(restored)}
        path.write_text(json.dumps(record), encoding="utf-8")
        return {"V2_ARCHIVE_RESTORE_APPROVED": "true",
                "V2_ARCHIVE_RESTORE_EVIDENCE": str(path)}

    def test_complete_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(check(self.evidence(directory)))

    def test_mismatched_restored_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.evidence(directory, "a" * 64)
            with self.assertRaisesRegex(RuntimeError, "integrity mismatch"):
                check(env)

    def test_missing_restored_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.evidence(directory)
            (Path(directory) / "restored.bin").unlink()
            with self.assertRaisesRegex(RuntimeError, "not found"):
                check(env)

if __name__ == "__main__":
    unittest.main()
