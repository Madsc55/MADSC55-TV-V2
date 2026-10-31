#!/usr/bin/env python3
"""No-network tests for private independent restore evidence acceptance."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from archive_acceptance_gate import check

class EvidenceSafetyTests(unittest.TestCase):
    def test_reject_world_readable_restored_archive(self):
        with tempfile.TemporaryDirectory() as d:
            restored = Path(d) / "restored.enc"
            restored.write_bytes(b"encrypted-fixture")
            restored.chmod(0o644)
            evidence = Path(d) / "evidence.json"
            evidence.write_text(json.dumps({
                "encrypted": True, "durable": True, "restore_test_passed": True,
                "integrity_verified": True, "backup_location": "independent-backup",
                "restore_sha256": hashlib.sha256(restored.read_bytes()).hexdigest(),
                "restored_file": str(restored)}))
            env = {"V2_ARCHIVE_RESTORE_APPROVED": "true",
                   "V2_ARCHIVE_RESTORE_EVIDENCE": str(evidence)}
            with self.assertRaisesRegex(RuntimeError, "owner-only"):
                check(env)
            restored.chmod(0o600)
            self.assertTrue(check(env))
    def test_reject_symlink_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            original = Path(d) / "original.json"
            original.write_text("{}")
            link = Path(d) / "link.json"
            link.symlink_to(original)
            with self.assertRaisesRegex(RuntimeError, "non-symlink"):
                check({"V2_ARCHIVE_RESTORE_APPROVED": "true",
                       "V2_ARCHIVE_RESTORE_EVIDENCE": str(link)})
if __name__ == "__main__":
    unittest.main(verbosity=2)
