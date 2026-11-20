import tempfile
import unittest
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

    def test_wrong_key_fails_closed(self):
        self.vault.add("tr1", "https://example.org/a", "source", True, True)
        with self.assertRaises(ValueError):
            Vault(self.vault.path, Fernet.generate_key()).read()

if __name__ == "__main__":
    unittest.main()
