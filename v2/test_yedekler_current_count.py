#!/usr/bin/env python3
"""Offline regression for current-size YEDEKLER archive and assignment."""
import json
import tempfile
import unittest
from pathlib import Path

from ibo_yedekler_archive import snapshot
from ibo_yedekler_assign import read_archive, initial_ledger, validate_ledger, plan, commit


class CurrentCountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "main.m3u8"
        self.source.write_text(
            '#EXTM3U\n'
            '#EXTINF:-1 group-title="OTHER",Other\nhttps://example.org/other\n'
            '#EXTINF:-1 group-title="YEDEKLER",One\nhttps://example.org/one\n'
            '#EXTINF:-1 group-title="YEDEKLER",Two\nhttps://example.org/two\n',
            encoding="utf-8")
        self.original = self.source.read_bytes()

    def test_current_size_and_idempotence(self):
        manifest = snapshot(self.source, self.root / "archive", expected_count=2)
        self.assertEqual(manifest["archived_count"], 2)
        self.assertEqual(manifest["expected_count"], 2)
        self.assertTrue(manifest["count_matches_expected"])
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(len(json.loads((self.root / "archive" / "manifest.json").read_text())["records"]), 2)
        sha, records = read_archive(self.source, expected_count=2)
        ledger = initial_ledger(sha, records)
        validate_ledger(ledger, sha, records)
        applied = commit(ledger, plan(ledger, records, 1, 1, "TURK"), 0)
        self.assertEqual(commit(applied, plan(applied, records, 1, 1, "TURK"), 1), applied)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_wrong_count_rejected_without_output(self):
        with self.assertRaises(ValueError):
            snapshot(self.source, self.root / "bad", expected_count=18074)
        self.assertFalse((self.root / "bad").exists())
        with self.assertRaises(ValueError):
            read_archive(self.source, expected_count=18074)

    def test_empty_group_and_invalid_guard_rejected(self):
        self.source.write_text('#EXTM3U\n#EXTINF:-1 group-title="OTHER",Other\nhttps://example.org/other\n')
        with self.assertRaises(ValueError):
            snapshot(self.source, self.root / "empty")
        with self.assertRaises(ValueError):
            read_archive(self.source)
        with self.assertRaises(ValueError):
            read_archive(self.source, expected_count=0)
        self.assertFalse((self.root / "empty").exists())


if __name__ == "__main__":
    unittest.main()
