import hashlib
import tempfile
import unittest
from pathlib import Path

from secure_archive import backup
from stage_c_verify_retrieved_archive import verify


class StageCRetrievedArchiveTests(unittest.TestCase):
    def test_valid_encrypted_restore_is_not_external_or_device_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "private.json"
            source.write_bytes(b'{"channels":[]}')
            archive = root / "private.aes"
            receipt = backup(source, archive, "long-private-test-passphrase")
            result = verify(archive, receipt["archive_sha256"],
                            receipt["restored_sha256"], "long-private-test-passphrase")
            self.assertTrue(result["restore_test_passed"])
            self.assertFalse(result["independent_storage_verified"])
            self.assertFalse(result["device_playback_verified"])

    def test_wrong_archive_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input"
            source.write_bytes(b"private")
            archive = root / "archive"
            receipt = backup(source, archive, "long-private-test-passphrase")
            with self.assertRaisesRegex(ValueError, "archive SHA256 mismatch"):
                verify(archive, "0" * 64, receipt["restored_sha256"],
                       "long-private-test-passphrase")

    def test_wrong_restored_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input"
            source.write_bytes(b"private")
            archive = root / "archive"
            receipt = backup(source, archive, "long-private-test-passphrase")
            with self.assertRaisesRegex(ValueError, "restored SHA256 mismatch"):
                verify(archive, receipt["archive_sha256"], "0" * 64,
                       "long-private-test-passphrase")

    def test_wrong_password_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input"
            source.write_bytes(b"private")
            archive = root / "archive"
            receipt = backup(source, archive, "long-private-test-passphrase")
            with self.assertRaises(Exception):
                verify(archive, receipt["archive_sha256"], receipt["restored_sha256"],
                       "different-private-passphrase")


if __name__ == "__main__":
    unittest.main()
