#!/usr/bin/env python3
"""Offline encryption and restore regression tests."""
import tempfile
import unittest
from pathlib import Path
from cryptography.exceptions import InvalidTag
from secure_archive import encrypt, decrypt, backup, restore

SECRET = 'test-only-passphrase-strong-enough'

class SecureArchiveTests(unittest.TestCase):
    def test_roundtrip_and_tamper_detection(self):
        raw = b'#EXTM3U\nhttps://example.invalid/live?token=private\n'
        blob = encrypt(raw, SECRET)
        self.assertNotIn(b'example.invalid', blob)
        self.assertEqual(decrypt(blob, SECRET), raw)
        with self.assertRaises(InvalidTag):
            decrypt(blob, 'wrong-passphrase-123456789')
        changed = bytearray(blob)
        changed[-1] ^= 1
        with self.assertRaises(InvalidTag):
            decrypt(bytes(changed), SECRET)

    def test_backup_and_restore_on_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, archive, restored = (root / x for x in ('source.jsonl', 'vault.enc', 'restored.jsonl'))
            source.write_bytes(b'{"url":"https://example.invalid/private"}\n')
            result = backup(source, archive, SECRET)
            self.assertTrue(result['restore_test_passed'])
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
            restore(archive, restored, SECRET)
            self.assertEqual(source.read_bytes(), restored.read_bytes())

    def test_malformed_and_truncated_archives_rejected(self):
        for blob in (b'', b'not-an-archive', b'MADSC55-V2-ARCHIVE\\x01'):
            with self.assertRaises(ValueError):
                decrypt(blob, SECRET)

    def test_backup_and_restore_refuse_same_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'same.bin'
            source.write_bytes(b'private')
            with self.assertRaises(ValueError):
                backup(source, source, SECRET)
            with self.assertRaises(ValueError):
                restore(source, source, SECRET)

    def test_short_secret_rejected(self):
        with self.assertRaises(ValueError):
            encrypt(b'abc', 'short')

if __name__ == '__main__':
    unittest.main(verbosity=2)
