#!/usr/bin/env python3
"""Offline private encrypted vault restore acceptance; no Drive or streaming access."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from cryptography.fernet import Fernet
from v2.authorized_vault_external_restore_acceptance import verify_retrieved_vault
from v2.turk_authorized_vault import Vault


class ExternalVaultAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = Fernet.generate_key()
        self.source = self.root / "private-vault.enc"
        self.external = self.root / "downloaded-vault.enc"
        self.vault = Vault(self.source, self.key)
        self.vault.add(
            "channel-id-not-for-public-reports",
            "https://licensed.example.test/stream?secret=KEEP_PRIVATE",
            "authorized licensed provenance",
            True, True)
        self.sha = self.vault.backup(self.external)

    def verify(self, **kwargs):
        return verify_retrieved_vault(
            kwargs.get("source", self.source), kwargs.get("external", self.external),
            kwargs.get("sha", self.sha), kwargs.get("key", self.key))

    def test_success_keeps_urls_identifiers_and_secrets_private(self):
        proof = self.verify()
        self.assertTrue(proof["encrypted_source_and_copy_byte_identical"])
        self.assertTrue(proof["isolated_restore_contents_identical"])
        self.assertTrue(proof["isolated_restore_private_permissions"])
        self.assertEqual(proof["restored_entry_count"], 1)
        self.assertEqual(proof["network_requests"], 0)
        self.assertFalse(proof["external_provider_identity_verified_by_this_tool"])
        self.assertFalse(proof["full_external_acceptance"])
        serialized = json.dumps(proof)
        for secret in ("KEEP_PRIVATE", "licensed.example", "channel-id-not-for-public-reports",
                       "authorized licensed provenance", self.key.decode()):
            self.assertNotIn(secret, serialized)
        self.assertFalse((self.root / "restored-private.enc").exists())

    def test_rejects_wrong_key(self):
        with self.assertRaises(ValueError):
            self.verify(key=Fernet.generate_key())

    def test_rejects_changed_retrieved_copy(self):
        self.external.write_bytes(self.external.read_bytes() + b"tamper")
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            self.verify()

    def test_rejects_unpinned_or_incorrect_digest(self):
        for sha in ("", "b" * 64, "f" * 63, "X" * 64):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                self.verify(sha=sha)

    def test_rejects_same_file_and_hardlink(self):
        with self.assertRaisesRegex(ValueError, "different files"):
            self.verify(external=self.source)
        hardlink = self.root / "same-inode.enc"
        os.link(self.source, hardlink)
        with self.assertRaisesRegex(ValueError, "different files"):
            self.verify(external=hardlink)

    def test_rejects_symlink_and_nonprivate_download(self):
        link = self.root / "linked.enc"
        link.symlink_to(self.external)
        with self.assertRaises((ValueError, OSError)):
            self.verify(external=link)
        self.external.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "private"):
            self.verify()

    def test_rejects_missing_key_or_missing_source(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.verify(key=None)
        self.source.unlink()
        with self.assertRaises(FileNotFoundError):
            self.verify()

    def test_rejects_encrypted_foreign_channel_policy(self):
        document = self.vault.read()
        document["entries"]["channel-id-not-for-public-reports"]["turkish"] = False
        blob = self.vault.cipher.encrypt(json.dumps(document).encode("utf-8"))
        self.source.write_bytes(blob)
        self.external.write_bytes(blob)
        digest = hashlib.sha256(blob).hexdigest()
        with self.assertRaisesRegex(ValueError, "policy"):
            self.verify(sha=digest)


if __name__ == "__main__":
    unittest.main()
