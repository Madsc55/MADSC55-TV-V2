import unittest
from secure_archive import encrypt
from verify_external_archive_bytes import verify


class ExternalArchiveByteVerificationTests(unittest.TestCase):
    def setUp(self):
        self.raw = b"realistic offline fixture, not production evidence"
        self.password = "offline-test-passphrase-2026"
        self.encrypted = encrypt(self.raw, self.password)

    def test_authenticated_bytes_and_no_false_production_attestation(self):
        result = verify(self.raw, self.encrypted, self.raw, self.password)
        self.assertEqual(result["status"], "LOCAL_CRYPTOGRAPHIC_VERIFICATION_ONLY")
        self.assertTrue(result["external_restore_verified"])
        self.assertFalse(result["independent_production_restore_accepted"])
        self.assertFalse(result["storage_provenance_verified"])
        self.assertEqual(len(result["external_archive_sha256"]), 64)

    def test_rejects_mismatched_restore(self):
        with self.assertRaises(ValueError):
            verify(self.raw, self.encrypted, b"tampered", self.password)

    def test_rejects_wrong_password(self):
        with self.assertRaises(Exception):
            verify(self.raw, self.encrypted, self.raw, "wrong")

    def test_rejects_missing_secret(self):
        with self.assertRaises(ValueError):
            verify(self.raw, self.encrypted, self.raw, "")

    def test_rejects_plaintext_as_encrypted_archive(self):
        with self.assertRaises(ValueError):
            verify(self.raw, self.raw, self.raw, self.password)


if __name__ == "__main__":
    unittest.main()
