#!/usr/bin/env python3
"""Offline lossless backup/restore regression; no production playlist writes."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ibo_archive_verify", ROOT / "v2" / "ibo_archive_verify.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ArchiveRestoreTest(unittest.TestCase):
    def test_live_playlist_roundtrip(self):
        source = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
        before = source.read_bytes()
        records = mod.inventory(before)
        backups = [r for r in records if "YEDEKLER" in r["metadata"]]
        self.assertGreaterEqual(len(backups), 2)
        self.assertIn("TRT 1", backups[0]["name"])
        self.assertIn("DHA", backups[1]["name"])
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "archive.json"
            restored = Path(tmp) / "restored.m3u8"
            self.assertEqual(mod.archive(source, archive), len(records))
            self.assertEqual(mod.restore(archive, restored), len(records))
            self.assertEqual(restored.read_bytes(), before)
            with self.assertRaises(FileExistsError):
                mod.restore(archive, restored)
            payload = json.loads(archive.read_text())
            payload["sha256"] = "0" * 64
            archive.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                mod.restore(archive, Path(tmp) / "tampered.m3u8")
        self.assertEqual(source.read_bytes(), before)

if __name__ == "__main__":
    unittest.main()
