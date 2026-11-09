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

    def test_tampered_baseline_metadata_with_same_sha_identities_is_rejected(self):
        """Changing reference metadata cannot redefine the immutable baseline."""
        lines = BASELINE.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[0])
        record["source"] = "TAMPERED_REFERENCE_METADATA"
        lines[0] = json.dumps(record, ensure_ascii=False)
        modified = self.root / "tampered-baseline.jsonl"
        modified.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with patch("archive_acceptance_gate.BASELINE", modified):
            with self.assertRaisesRegex(RuntimeError, "historical identities or metadata"):
                check(self.prepared())

    def test_authenticated_candidate_without_raw_url_provenance_rejected(self):
        """Even a fully encrypted view cannot invent a playable URL."""
        from historical_inventory_guard import preserve_to_new_archive
        history = [json.loads(line) for line in BASELINE.read_text().splitlines() if line]
        forged = [{"url": "https://fixture.example.org/forged.m3u8",
                   "source_ids": ["invented"], "status": "NOT_REVERIFIED"}]
        archive = self.root / "forged-view.enc"
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            preserve_to_new_archive(archive, history, forged)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        env = self.prepared(restored_file=str(archive), restore_sha256=digest)
        env["V2_ARCHIVE_EXPECTED_SHA256"] = digest
        with self.assertRaisesRegex(RuntimeError, "lacks raw URL provenance"):
            check(env)

    def test_authenticated_candidate_cannot_claim_fresh_av(self):
        """Matching URL provenance still cannot manufacture decoded playback."""
        from historical_inventory_guard import preserve_to_new_archive, reconcile
        history = [json.loads(line) for line in BASELINE.read_text().splitlines() if line]
        url = "https://fixture.example.org/historical-candidate.m3u8"
        current = [{"url": url, "source_id": "fixture"}]
        protected, candidates, _ = reconcile(history, current, 4955)
        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0]["av_verified"])
        candidates[0]["av_verified"] = True
        archive = self.root / "forged-fresh-av.enc"
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            preserve_to_new_archive(archive, protected, candidates)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        env = self.prepared(restored_file=str(archive), restore_sha256=digest)
        env["V2_ARCHIVE_EXPECTED_SHA256"] = digest
        with self.assertRaisesRegex(RuntimeError, "falsely claims fresh AV"):
            check(env)

    def test_hash_only_candidate_cannot_pass_as_real_url_view(self):
        """A matching digest alone does not create a playable candidate URL."""
        from historical_inventory_guard import digest, preserve_to_new_archive, reconcile
        history = [json.loads(line) for line in BASELINE.read_text().splitlines() if line]
        url = "https://fixture.example.org/source-url.m3u8"
        protected, candidates, _ = reconcile(history, [{"url": url}], 4955)
        self.assertEqual(len(candidates), 1)
        candidates[0].pop("url")
        self.assertEqual(candidates[0]["url_sha256"], digest(url))
        archive = self.root / "hash-only-candidate.enc"
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            preserve_to_new_archive(archive, protected, candidates)
        digest_value = hashlib.sha256(archive.read_bytes()).hexdigest()
        env = self.prepared(restored_file=str(archive), restore_sha256=digest_value)
        env["V2_ARCHIVE_EXPECTED_SHA256"] = digest_value
        with self.assertRaisesRegex(RuntimeError, "lacks raw URL provenance"):
            check(env)

    def test_encrypted_candidate_cannot_claim_ibo_device_acceptance(self):
        """A real URL and authentic archive are not device playback proof."""
        from historical_inventory_guard import preserve_to_new_archive, reconcile
        history = [json.loads(line) for line in BASELINE.read_text().splitlines() if line]
        raw, view, _ = reconcile(history, [
            {"url": "https://fixture.example.org/ibo-candidate.m3u8"}], 4955)
        self.assertEqual(len(view), 1)
        for field in ("device_verified", "ibo_device_verified"):
            with self.subTest(field=field):
                forged = [dict(view[0], **{field: True})]
                archive = self.root / (field + "-forged.enc")
                with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
                    preserve_to_new_archive(archive, raw, forged)
                digest = hashlib.sha256(archive.read_bytes()).hexdigest()
                env = self.prepared(restored_file=str(archive), restore_sha256=digest)
                env["V2_ARCHIVE_EXPECTED_SHA256"] = digest
                with self.assertRaisesRegex(RuntimeError, "falsely claims fresh AV"):
                    check(env)

    def test_missing_approval_or_evidence(self):
        with self.assertRaises(RuntimeError): check({})
        with self.assertRaises(RuntimeError): check({"V2_ARCHIVE_RESTORE_APPROVED": "true"})

    def test_no_local_or_unversioned_backup(self):
        for changed in ({"backup_scope": "local_separate_directory_not_independent_storage"},
                        {"backup_location": "file:///tmp/archive.enc"},
                        {"remote_object_version": ""},
                        {"remote_object_version": "null"},
                        {"retrieval_method": "unverified_copy"},
                        {"historical_record_count": 4954}):
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                check(self.prepared(**changed))

    def test_reject_control_character_in_remote_version_evidence(self):
        for invalid in ("revision" + chr(127), "revision\nnext", "revision\t"):
            with self.subTest(version=repr(invalid)):
                with self.assertRaisesRegex(RuntimeError, "immutable"):
                    check(self.prepared(remote_object_version=invalid))

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
