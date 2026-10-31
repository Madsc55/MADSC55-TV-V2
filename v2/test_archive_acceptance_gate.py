#!/usr/bin/env python3
"""Offline archive gate tests: absent, incomplete, and valid evidence."""
import json
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
    def test_complete_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps({"encrypted": True, "durable": True, "restore_test_passed": True, "integrity_verified": True, "backup_location": "secure-store", "restore_sha256": "a"*64}), encoding="utf-8")
            self.assertTrue(check({"V2_ARCHIVE_RESTORE_APPROVED": "true", "V2_ARCHIVE_RESTORE_EVIDENCE": str(path)}))

if __name__ == "__main__":
    unittest.main()
