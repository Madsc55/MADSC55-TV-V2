#!/usr/bin/env python3
"""Offline encrypted backup restore drill regression."""
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from archive_backup_restore_drill import drill
from encrypted_archive import append, restore

class BackupRestoreDrillTests(unittest.TestCase):
    def test_private_backup_restores_original_records(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "independent").mkdir()
            source = root / "archive.enc"
            key = "ab" * 32
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": key}):
                append(source, {"url": "https://example.org/live.m3u8?token=PRIVATE"})
                result = drill(source, root / "independent" / "copy.enc",
                               root / "restored.enc", root / "evidence.json")
                self.assertEqual(result["record_count"], 1)
                self.assertIs(result["durable"], False)
                self.assertEqual(result["backup_scope"], "local_separate_directory_not_independent_storage")
                self.assertEqual(restore(root / "restored.enc"), restore(source))
                self.assertEqual((root / "restored.enc").stat().st_mode & 0o077, 0)
                self.assertNotIn("PRIVATE", (root / "evidence.json").read_text())
                with self.assertRaisesRegex(RuntimeError, "must not exist"):
                    drill(source, root / "independent" / "copy.enc",
                          root / "another.enc", root / "other.json")
    def test_reject_same_backup_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            source = root / "archive.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "cd" * 32}):
                append(source, {"url": "https://example.org/live.m3u8"})
                with self.assertRaisesRegex(RuntimeError, "separate directory"):
                    drill(source, root / "backup.enc", root / "restore.enc", root / "evidence.json")
if __name__ == "__main__":
    unittest.main(verbosity=2)
