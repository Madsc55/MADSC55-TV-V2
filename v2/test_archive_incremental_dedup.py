#!/usr/bin/env python3
"""Offline regression: repeat discovery must not duplicate previously encrypted URLs."""
import tempfile
import unittest
from pathlib import Path
from encrypted_archive import append, restore

KEY = "a1" * 32

class ArchiveDedupTests(unittest.TestCase):
    def test_existing_archive_urls_are_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "candidates.enc"
            append(path, {"source": "first", "url": "https://example.org/a.m3u8"}, KEY)
            known = {record["url"] for record in restore(path, KEY)}
            self.assertIn("https://example.org/a.m3u8", known)
            self.assertNotIn("https://example.org/b.m3u8", known)
            for url in ("https://example.org/a.m3u8", "https://example.org/b.m3u8"):
                if url not in known:
                    append(path, {"source": "second", "url": url}, KEY)
                    known.add(url)
            records = restore(path, KEY)
            self.assertEqual(len(records), 2)
            self.assertEqual({r["url"] for r in records}, known)
if __name__ == "__main__":
    unittest.main(verbosity=2)
