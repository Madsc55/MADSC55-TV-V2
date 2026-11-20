#!/usr/bin/env python3
"""Offline, no-key, no-network archive format regression."""
import json
import tempfile
import unittest
from pathlib import Path
from archive_format_preflight import inspect, MAGIC


class ArchiveFormatPreflightTest(unittest.TestCase):
    def test_binary_archive(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "v2.enc"
            p.write_bytes(MAGIC + b"synthetic")
            self.assertTrue(inspect(p)["compatible_with_secure_archive"])

    def test_legacy_jsonl_rejected_for_binary_restore(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "old.enc"
            record = json.dumps({"schema": 1, "nonce": "test", "ciphertext": "fake"})
            p.write_text(record + "\n" + record + "\n")
            result = inspect(p)
            self.assertEqual(result["records"], 2)
            self.assertFalse(result["compatible_with_secure_archive"])

    def test_unknown_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.enc"
            p.write_text('{"schema":1,"nonce":"a"}\n')
            with self.assertRaises(ValueError):
                inspect(p)
            link = Path(d) / "link.enc"
            link.symlink_to(p)
            with self.assertRaises(ValueError):
                inspect(link)


if __name__ == "__main__":
    unittest.main()
