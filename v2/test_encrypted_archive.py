#!/usr/bin/env python3
"""Offline encrypted archive integrity and tamper tests."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from encrypted_archive import append, restore, archive_sha256, archive_manifest, restore_verified

KEY = "ab" * 32

class EncryptedArchiveTests(unittest.TestCase):
    def test_roundtrip_append_and_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            records = [{"url": "https://example.invalid/private.m3u8?token=secret"},
                       {"url": "https://example.invalid/second.m3u8"}]
            for record in records:
                append(path, record, KEY)
            raw = path.read_bytes()
            self.assertNotIn(b"token=secret", raw)
            self.assertEqual(restore(path, KEY), records)
            self.assertEqual(len(archive_sha256(path)), 64)
            self.assertEqual(path.stat().st_mode & 0o077, 0)
    def test_manifest_detects_whole_record_deletion_and_reordering(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            rows = [{"id": 1}, {"id": 2}, {"id": 3}]
            for row in rows:
                append(path, row, KEY)
            manifest = archive_manifest(path, KEY)
            self.assertEqual(manifest["record_count"], 3)
            self.assertEqual(restore_verified(path, manifest, KEY), rows)
            lines = path.read_bytes().splitlines(keepends=True)
            path.write_bytes(lines[0] + lines[2])
            with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                restore_verified(path, manifest, KEY)
            path.write_bytes(lines[1] + lines[0] + lines[2])
            with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                restore_verified(path, manifest, KEY)

    def test_manifest_detects_mutation_during_creation(self):
        from unittest.mock import patch
        import encrypted_archive as archive
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            append(path, {"id": 1}, KEY)
            original_restore = archive.restore
            def mutate_after_restore(p, key):
                rows = original_restore(p, key)
                append(p, {"id": 2}, key)
                return rows
            with patch.object(archive, "restore", side_effect=mutate_after_restore):
                with self.assertRaisesRegex(ValueError, "changed during manifest creation"):
                    archive_manifest(path, KEY)

    def test_manifest_detects_mutation_during_restore(self):
        from unittest.mock import patch
        import encrypted_archive as archive
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            append(path, {"id": 1}, KEY)
            manifest = archive_manifest(path, KEY)
            original_restore = archive.restore
            def mutate_after_restore(p, key):
                rows = original_restore(p, key)
                append(p, {"id": 2}, key)
                return rows
            with patch.object(archive, "restore", side_effect=mutate_after_restore):
                with self.assertRaisesRegex(ValueError, "changed during verified restore"):
                    restore_verified(path, manifest, KEY)

    def test_manifest_invalid_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            append(path, {"id": 1}, KEY)
            manifest = archive_manifest(path, KEY)
            manifest["record_count"] = 2
            with self.assertRaisesRegex(ValueError, "count mismatch"):
                restore_verified(path, manifest, KEY)

    def test_truncated_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            append(path, {"url": "https://example.invalid/first.m3u8"}, KEY)
            append(path, {"url": "https://example.invalid/second.m3u8"}, KEY)
            raw = path.read_bytes()
            path.write_bytes(raw[:-12])
            with self.assertRaises(Exception):
                restore(path, KEY)

    def test_complete_json_without_newline_is_incomplete_record(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.jsonl.enc"
            append(path, {"url": "https://example.invalid/valid.m3u8"}, KEY)
            data = path.read_bytes()
            self.assertTrue(data.endswith(b"\n"))
            path.write_bytes(data[:-1])
            with self.assertRaisesRegex(ValueError, "Incomplete archive record"):
                restore(path, KEY)

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
    def test_symlink_restore_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "real.enc"
            append(target, {"a": 1}, KEY)
            link = Path(folder) / "link.enc"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                restore(link, KEY)
    def test_public_permissions_restore_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "real.enc"
            append(target, {"a": 1}, KEY)
            target.chmod(0o644)
            with self.assertRaises(PermissionError):
                restore(target, KEY)
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
