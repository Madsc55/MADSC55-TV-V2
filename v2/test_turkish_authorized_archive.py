import json
import tempfile
import unittest
from pathlib import Path
from turkish_authorized_archive import validate_inventory, archive_private, restore_private

RECORD = {"channel_id": "tr-demo", "country": "TR", "language": "tr",
          "url": "https://example.org/authorized.m3u8", "access": "licensed",
          "authorization_evidence": "offline-license-fixture",
          "provenance": "official-provider", "first_seen": "2026-11-20",
          "last_seen": "2026-11-20", "status": "authorization_required",
          "version": 1, "decision_history": []}

class TurkishArchiveTests(unittest.TestCase):
    def test_private_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, encrypted, restored = (root / name for name in
                                           ("private.jsonl", "private.enc", "restored.jsonl"))
            source.write_text(json.dumps(RECORD) + "\n", encoding="utf-8")
            result = archive_private(source, encrypted, "offline-test-passphrase-only")
            self.assertEqual(result["records"], 1)
            self.assertTrue(result["restore_test_passed"])
            self.assertNotIn(b"authorized.m3u8", encrypted.read_bytes())
            self.assertEqual(restore_private(encrypted, restored,
                                             "offline-test-passphrase-only")["records"], 1)
            self.assertEqual(restored.read_bytes(), source.read_bytes())

    def test_foreign_channel_rejected(self):
        with self.assertRaisesRegex(ValueError, "Non-Turkish"):
            validate_inventory((json.dumps({**RECORD, "country": "US", "language": "en"}) + "\n").encode())

    def test_missing_license_rejected(self):
        with self.assertRaisesRegex(ValueError, "Authorization"):
            validate_inventory((json.dumps({**RECORD, "authorization_evidence": ""}) + "\n").encode())

    def test_duplicate_rejected(self):
        line = (json.dumps(RECORD) + "\n").encode()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_inventory(line + line)

    def test_existing_restore_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, encrypted, restored = (root / name for name in
                                           ("private.jsonl", "private.enc", "restored.jsonl"))
            source.write_text(json.dumps(RECORD) + "\n", encoding="utf-8")
            archive_private(source, encrypted, "offline-test-passphrase-only")
            restored.write_bytes(b"PROTECTED")
            with self.assertRaises(FileExistsError):
                restore_private(encrypted, restored, "offline-test-passphrase-only")
            self.assertEqual(restored.read_bytes(), b"PROTECTED")

if __name__ == "__main__":
    unittest.main()
