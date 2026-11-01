#!/usr/bin/env python3
import os
import tempfile
import unittest
from pathlib import Path
import private_archive as archive

class ArchiveTests(unittest.TestCase):
    def test_roundtrip(self):
        key = os.urandom(32)
        payload = b"example inventory"
        sealed = archive.encrypt(payload, key)
        self.assertEqual(archive.decrypt(sealed, key), payload)

    def test_reject_corruption(self):
        key = os.urandom(32)
        sealed = archive.encrypt(b"example inventory", key)
        modified = sealed[:-1] + bytes([sealed[-1] ^ 1])
        with self.assertRaises(Exception):
            archive.decrypt(modified, key)

    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "test.bin"
            archive.atomic_private_write(target, b"content")
            self.assertEqual(target.read_bytes(), b"content")

if __name__ == "__main__":
    unittest.main()
