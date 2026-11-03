#!/usr/bin/env python3
"""Independent restore safety rejects the former plaintext-positive fixture."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from archive_acceptance_gate import check

class EvidenceSafetyTests(unittest.TestCase):
    def test_fake_archive_rejected_even_if_checksummed(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "fake.enc"
            fake.write_bytes(b"not encrypted")
            fake.chmod(0o600)
            sha = hashlib.sha256(fake.read_bytes()).hexdigest()
            evidence = Path(folder) / "evidence.json"
            evidence.write_text(json.dumps({
                "encrypted": True, "durable": True, "restore_test_passed": True,
                "integrity_verified": True, "backup_scope": "independent_remote_storage",
                "retrieval_method": "aws_s3api_versioned_get_object",
                "backup_location": "s3://versioned-store/v2/archive.enc",
                "remote_object_version": "v1", "historical_record_count": 4955,
                "restore_sha256": sha, "restored_file": str(fake)}))
            evidence.chmod(0o600)
            env = {"V2_ARCHIVE_RESTORE_APPROVED": "true",
                   "V2_ARCHIVE_RESTORE_EVIDENCE": str(evidence),
                   "V2_ARCHIVE_EXPECTED_SHA256": sha,
                   "V2_ARCHIVE_KEY_HEX": "ab" * 32}
            with self.assertRaisesRegex(RuntimeError, "AES-GCM"): check(env)
            fake.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError, "owner-only"): check(env)

    def test_reject_symlink_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "real.json"
            path.write_text("{}")
            link = Path(folder) / "link.json"
            link.symlink_to(path)
            with self.assertRaisesRegex(RuntimeError, "non-symlink"):
                check({"V2_ARCHIVE_RESTORE_APPROVED": "true",
                       "V2_ARCHIVE_RESTORE_EVIDENCE": str(link)})

if __name__ == "__main__":
    unittest.main(verbosity=2)
