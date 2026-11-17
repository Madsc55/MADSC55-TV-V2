#!/usr/bin/env python3
"""Offline tests for URL duplicate guard, no network or stream probes."""
import tempfile
import unittest
from pathlib import Path
from ibo_archive_url_dedup import inspect


class DuplicateGuardTests(unittest.TestCase):
    def test_exact_url_and_query_params(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main = root / "main.m3u8"
            archive = root / "archive.m3u8"
            candidates = root / "new.m3u8"
            main.write_text("#EXTM3U\n#EXTINF:-1,One\nhttps://tv.example/live?id=1\n")
            archive.write_text("#EXTM3U\n#EXTINF:-1,One\nhttps://tv.example/live?id=1\n")
            candidates.write_text("#EXTM3U\nhttps://tv.example/live?id=1\nhttps://tv.example/live?id=2\nhttps://tv.example/live?id=2\n")
            result = inspect(main, archive, candidates)
            self.assertEqual(result["existing_unique_urls"], 1)
            self.assertEqual(result["accepted_count"], 1)
            self.assertEqual(result["duplicate_count"], 2)
            self.assertNotIn("https://", str(result))


if __name__ == "__main__":
    unittest.main()
