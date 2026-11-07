#!/usr/bin/env python3
"""Grouped, offline acceptance for the 17 preserved run-60 source identities."""
import json
import tempfile
import unittest
from pathlib import Path

from discover import load_original_run60_sources, normalize_original_source_text

LEDGER = Path(__file__).resolve().parent / "history" / "run60-dynamic-source-ledger.json"


class OriginalRun60LedgerTests(unittest.TestCase):
    def setUp(self):
        self.original = json.loads(LEDGER.read_text(encoding="utf-8"))

    def load_modified(self, document):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            return load_original_run60_sources(path)

    def test_preserves_all_17_unique_sources_and_8449_old_only(self):
        rows = self.load_modified(self.original)
        self.assertEqual(len(rows), 17)
        self.assertEqual(len({row["id"] for row in rows}), 17)
        self.assertEqual(len({row["url"] for row in rows}), 17)
        self.assertEqual(sum(row["old_only"] for row in self.original["sources"]), 8449)
        self.assertTrue(all(row["historical_source_only"] for row in rows))

    def test_duplicate_url_rejected_even_with_distinct_identity(self):
        document = json.loads(json.dumps(self.original))
        document["sources"][1]["url"] = document["sources"][0]["url"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.load_modified(document)

    def test_duplicate_identity_rejected(self):
        document = json.loads(json.dumps(self.original))
        document["sources"][1]["id"] = document["sources"][0]["id"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.load_modified(document)

    def test_missing_and_private_source_urls_rejected(self):
        for invalid in ("", "http://raw.githubusercontent.com/a/b/main/x.m3u",
                        "https://localhost/x.m3u", "https://raw.githubusercontent.com/a/b/main/x.txt",
                        "https://raw.githubusercontent.com:bad/a/b/main/x.m3u",
                        "https://[broken/a/b/main/x.m3u"):
            with self.subTest(invalid=invalid):
                document = json.loads(json.dumps(self.original))
                document["sources"][0]["url"] = invalid
                with self.assertRaises(ValueError):
                    self.load_modified(document)

    def test_malformed_source_rows_and_counts_rejected_without_crash(self):
        malformed = (None, [], "not-a-record", {"id": "github-auto-0"},
                     {"old_only": "8449"}, {"old_only": True},
                     {"old_only": -1})
        for value in malformed:
            with self.subTest(value=value):
                document = json.loads(json.dumps(self.original))
                document["sources"][0] = value
                with self.assertRaises(ValueError):
                    self.load_modified(document)

    def test_headerless_historical_feed_only_normalized_for_verified_source(self):
        feed = "#EXTINF:-1,Historical\nhttps://example.org/a.m3u8\n"
        self.assertTrue(normalize_original_source_text({"historical_source_only": True}, feed).startswith("#EXTM3U\n"))
        self.assertEqual(normalize_original_source_text({}, feed), feed)


if __name__ == "__main__":
    unittest.main()
