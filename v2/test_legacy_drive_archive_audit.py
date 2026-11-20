#!/usr/bin/env python3
"""Offline tests for read-only legacy archive checks; no real secrets."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from legacy_drive_archive_audit import audit, PRODUCTION_MAGIC


class LegacyDriveArchiveAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "sample.enc"

    def record(self, nonce):
        return json.dumps({"schema": 1,
                           "nonce": base64.b64encode(nonce).decode(),
                           "ciphertext": base64.b64encode(b"X" * 32).decode()}).encode()

    def test_stage4_valid(self):
        self.path.write_bytes(self.record(b"a" * 12) + b"\n" + self.record(b"b" * 12) + b"\n")
        result = audit(self.path)
        self.assertTrue(result["structural_pass"])
        self.assertFalse(result["restore_verified"])
        self.assertEqual(result["records"], 2)

    def test_nonce_reuse_rejected(self):
        self.path.write_bytes(self.record(b"a" * 12) + b"\n" + self.record(b"a" * 12))
        with self.assertRaisesRegex(ValueError, "reused nonce"):
            audit(self.path)

    def test_bad_ciphertext_rejected(self):
        self.path.write_bytes(b'{"schema":1,"nonce":"YWFhYWFhYWFhYWFh","ciphertext":"not base64!"}')
        with self.assertRaises(ValueError):
            audit(self.path)

    def test_duplicate_json_key_rejected(self):
        self.path.write_bytes(b'{"schema":1,"schema":1,"nonce":"YWFhYWFhYWFhYWFh","ciphertext":"QUFBQUFBQUFBQUFBQUFBQQ=="}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            audit(self.path)

    def test_production_header_only(self):
        self.path.write_bytes(PRODUCTION_MAGIC + b"X" * 64)
        result = audit(self.path)
        self.assertTrue(result["structural_pass"])
        self.assertFalse(result["restore_verified"])

    def test_symlink_rejected(self):
        source = Path(self.temp.name) / "source"
        source.write_bytes(PRODUCTION_MAGIC + b"X" * 64)
        self.path.symlink_to(source)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            audit(self.path)


if __name__ == "__main__":
    unittest.main()
