#!/usr/bin/env python3
"""Offline encrypted archive integrity and tamper tests."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from encrypted_archive import append, restore, archive_sha256

KEY = "ab" * 32

class EncryptedArchiveTests(unittest.TestCase):
    def test_roundtrip_append_and_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            append(path, {"url": "https://example.invalid/private.m3u8?token=secret"}, KEY)
            append(path, {"url": "https://example.invalid/second.m3u8"}, KEY)
            raw = path.read_bytes()
            self.assertNotIn(b"token=secret", raw)
            self.assertEqual(len(restore(path, KEY)), 2)
            self.assertEqual(len(archive_sha256(path)), 64)
            self.assertEqual(path.stat().st_mode & 0o077, 0)
    def test_tamper_fails_authentication(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            append(path, {"url": "https://example.invalid/live"}, KEY)
            data = json.loads(path.read_text())
            import base64
            cipher = bytearray(base64.b64decode(data["ciphertext"]))
            cipher[-1] ^= 1
            data["ciphertext"] = base64.b64encode(cipher).decode()
            path.write_text(json.dumps(data) + "\n")
            with self.assertRaises(Exception):
                restore(path, KEY)
    def test_symlink_destination_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "target"
            target.write_bytes(b"protected")
            link = Path(folder) / "archive.jsonl.enc"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                append(link, {"a": 1}, KEY)
            self.assertEqual(target.read_bytes(), b"protected")
    def test_bad_key_rejected(self):
        with self.assertRaises(ValueError):
            append("never-created", {"a": 1}, "short")
    def test_wrong_key_fails_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            append(path, {"a": 1}, KEY)
            with self.assertRaises(Exception):
                restore(path, "cd" * 32)

if __name__ == "__main__":
    unittest.main(verbosity=2)
