import os
import tempfile
import unittest
from unittest.mock import patch
import v2.turk_authorized_vault as vault_module
from pathlib import Path
from cryptography.fernet import Fernet
from v2.turk_authorized_vault import Vault

class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = Fernet.generate_key()
        self.vault = Vault(self.root / "private.enc", self.key)

    def test_encrypted_and_history(self):
        self.vault.add("tr1", "https://example.org/stream?token=secret", "licensed provider", True, True)
        self.assertNotIn(b"secret", self.vault.path.read_bytes())
        self.vault.add("tr1", "https://example.org/stream?token=secret", "licensed provider", True, True)
        self.assertEqual(len(self.vault.read()["entries"]["tr1"]["history"]), 2)
        self.assertNotIn("secret", str(self.vault.public_report()))

    def test_reject_foreign_and_unauthorized(self):
        for authorized, turkish in ((False, True), (True, False), (False, False)):
            with self.assertRaises(ValueError):
                self.vault.add("x", "https://example.org/a", "source", authorized, turkish)
        self.assertFalse(self.vault.path.exists())

    def test_duplicate_rejected(self):
        self.vault.add("one", "https://example.org/a", "source", True, True)
        with self.assertRaises(ValueError):
            self.vault.add("two", "https://example.org/a", "source", True, True)

    def test_restore_and_checksum(self):
        self.vault.add("tr1", "https://example.org/a", "source", True, True)
        backup = self.root / "backup.enc"
        digest = self.vault.backup(backup)
        restored = Vault(self.root / "restored.enc", self.key)
        restored.restore(backup, digest)
        self.assertEqual(restored.read(), self.vault.read())
        with self.assertRaises(ValueError):
            restored.restore(backup, digest)
        with self.assertRaises(ValueError):
            Vault(self.root / "other.enc", self.key).restore(backup, "0" * 64)

    def test_reject_malformed_urls(self):
        for url in ("https://", "https://user:pass@example.org/a",
                    "https://example.org/a\\nInjected", "https://example.org:0/a",
                    "https://example.org:bad/a"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.vault.add("tr1", url, "source", True, True)

    def test_restore_rejects_encrypted_foreign_entry(self):
        self.vault.add("tr1", "https://example.org/a", "source", True, True)
        doc = self.vault.read()
        doc["entries"]["tr1"]["turkish"] = False
        tampered = self.root / "tampered.enc"
        tampered.write_bytes(self.vault.cipher.encrypt(
            __import__("json").dumps(doc).encode()))
        restored = Vault(self.root / "restored.enc", self.key)
        import hashlib
        with self.assertRaises(ValueError):
            restored.restore(tampered, hashlib.sha256(tampered.read_bytes()).hexdigest())
        self.assertFalse(restored.path.exists())

    def test_private_permissions_and_symlink_rejection(self):
        self.vault.add("tr1", "https://example.org/a", "source", True, True)
        self.assertEqual(self.vault.path.stat().st_mode & 0o777, 0o600)
        self.vault.path.chmod(0o644)
        with self.assertRaises(ValueError):
            self.vault.read()
        self.vault.path.chmod(0o600)
        backup = self.root / "backup.enc"
        digest = self.vault.backup(backup)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        backup.chmod(0o644)
        with self.assertRaises(ValueError):
            Vault(self.root / "restore.enc", self.key).restore(backup, digest)
        backup.chmod(0o600)
        link = self.root / "link.enc"
        link.symlink_to(backup)
        with self.assertRaises(ValueError):
            Vault(self.root / "restore.enc", self.key).restore(link, digest)

    def test_source_symlink_swap_does_not_expose_vault(self):
        self.vault.add("tr1", "https://example.org/a", "source", True, True)
        replacement = self.root / "replacement.enc"
        replacement.write_bytes(self.vault.path.read_bytes())
        replacement.chmod(0o600)
        original_open = os.open
        def swap_before_descriptor(path, flags, *args, **kwargs):
            if Path(path) == self.vault.path:
                self.vault.path.unlink()
                self.vault.path.symlink_to(replacement)
            return original_open(path, flags, *args, **kwargs)
        with patch.object(vault_module.os, "open", side_effect=swap_before_descriptor):
            with self.assertRaises(OSError):
                self.vault.read()

    def test_backup_rejects_missing_or_oversized_source(self):
        with self.assertRaises(ValueError):
            self.vault.backup(self.root / "missing-backup.enc")
        self.vault.add("tr1", "https://example.org/a", "source", True, True)
        with patch.object(vault_module, "MAX_VAULT_BYTES", 1):
            with self.assertRaisesRegex(ValueError, "maximum size"):
                self.vault.backup(self.root / "oversized-backup.enc")
        self.assertFalse((self.root / "oversized-backup.enc").exists())

    def test_restore_race_cannot_overwrite_destination(self):
        self.vault.add("tr1", "https://example.org/a", "source", True, True)
        backup = self.root / "race-backup.enc"
        digest = self.vault.backup(backup)
        destination = self.root / "raced-restore.enc"
        restored = Vault(destination, self.key)
        original_link = os.link
        def create_target_just_before_link(source, target, *args, **kwargs):
            if Path(target) == destination:
                destination.write_bytes(b"KEEP")
            return original_link(source, target, *args, **kwargs)
        with patch.object(vault_module.os, "link", side_effect=create_target_just_before_link):
            with self.assertRaises(FileExistsError):
                restored.restore(backup, digest)
        self.assertEqual(destination.read_bytes(), b"KEEP")

    def test_wrong_key_fails_closed(self):
        self.vault.add("tr1", "https://example.org/a", "source", True, True)
        with self.assertRaises(ValueError):
            Vault(self.vault.path, Fernet.generate_key()).read()

if __name__ == "__main__":
    unittest.main()
