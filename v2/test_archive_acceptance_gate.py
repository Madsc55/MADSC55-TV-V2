#!/usr/bin/env python3
"""Grouped encrypted archive acceptance tests: real crypto, no network."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from archive_acceptance_gate import BASELINE, check
from historical_inventory_guard import preserve_to_new_archive

class ArchiveGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        cls.archive = cls.root / "restored.enc"
        records = [json.loads(line) for line in BASELINE.read_text().splitlines() if line]
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            preserve_to_new_archive(cls.archive, records, [])
        cls.sha = hashlib.sha256(cls.archive.read_bytes()).hexdigest()

    def prepared(self, **changes):
        obj = {"encrypted": True, "durable": True, "restore_test_passed": True,
               "integrity_verified": True, "backup_scope": "independent_remote_storage",
               "retrieval_method": "aws_s3api_versioned_get_object",
               "backup_location": "s3://versioned-archive/v2/archive.enc",
               "remote_object_version": "revision-one",
               "historical_record_count": 4955,
               "restore_sha256": self.sha, "restored_file": str(self.archive)}
        obj.update(changes)
        path = self.root / "evidence.json"
        path.write_text(json.dumps(obj))
        path.chmod(0o600)
        return {"V2_ARCHIVE_RESTORE_APPROVED": "true",
                "V2_ARCHIVE_RESTORE_EVIDENCE": str(path),
                "V2_ARCHIVE_EXPECTED_SHA256": self.sha,
                "V2_ARCHIVE_KEY_HEX": "ab" * 32}

    def test_actual_4955_history_roundtrip(self):
        self.assertTrue(check(self.prepared()))

    def test_missing_approval_or_evidence(self):
        with self.assertRaises(RuntimeError): check({})
        with self.assertRaises(RuntimeError): check({"V2_ARCHIVE_RESTORE_APPROVED": "true"})

    def test_no_local_or_unversioned_backup(self):
        for changed in ({"backup_scope": "local_separate_directory_not_independent_storage"},
                        {"backup_location": "file:///tmp/archive.enc"},
                        {"remote_object_version": ""},
                        {"retrieval_method": "unverified_copy"},
                        {"historical_record_count": 4954}):
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                check(self.prepared(**changed))

    def test_independent_digest_and_key_required(self):
        env = self.prepared()
        env["V2_ARCHIVE_EXPECTED_SHA256"] = "f" * 64
        with self.assertRaisesRegex(RuntimeError, "pinned"): check(env)
        env = self.prepared()
        env["V2_ARCHIVE_KEY_HEX"] = "cd" * 32
        with self.assertRaisesRegex(RuntimeError, "AES-GCM"): check(env)

    def test_reject_plaintext_fixture_even_when_digest_matches(self):
        fake = self.root / "fake.enc"
        fake.write_bytes(b"not an encrypted V2 archive")
        fake.chmod(0o600)
        sha = hashlib.sha256(fake.read_bytes()).hexdigest()
        env = self.prepared(restored_file=str(fake), restore_sha256=sha)
        env["V2_ARCHIVE_EXPECTED_SHA256"] = sha
        with self.assertRaisesRegex(RuntimeError, "AES-GCM"): check(env)

    def test_refuse_public_evidence_or_archive(self):
        env = self.prepared()
        path = Path(env["V2_ARCHIVE_RESTORE_EVIDENCE"])
        path.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, "owner-only"): check(env)
        path.chmod(0o600)
        self.archive.chmod(0o644)
        try:
            with self.assertRaisesRegex(RuntimeError, "owner-only"): check(env)
        finally:
            self.archive.chmod(0o600)

if __name__ == "__main__":
    unittest.main(verbosity=2)
