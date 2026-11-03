#!/usr/bin/env python3
"""Offline regression for exact original #60 dynamic GitHub M3U integration."""
import json
from pathlib import Path
import tempfile
import unittest

from discover import load_original_run60_sources, normalize_original_source_text, entries


ROOT = Path(__file__).resolve().parent


class OriginalRun60DiscoveryTests(unittest.TestCase):
    def test_exact_original_17_sources_load_without_network_or_playlist_changes(self):
        loaded = load_original_run60_sources(
            ROOT / "history/run60-dynamic-source-ledger.json")
        self.assertEqual(len(loaded), 17)
        self.assertEqual(len({x["id"] for x in loaded}), 17)
        self.assertEqual(loaded[7]["id"], "github-auto-7")
        self.assertEqual(loaded[8]["id"], "github-auto-8")
        self.assertTrue(all(x["historical_source_only"] for x in loaded))
        self.assertEqual(loaded[8]["scope"], "candidate")

    def test_missing_header_can_be_normalized_only_for_proven_historical(self):
        raw = "#EXTINF:-1 tvg-id=\"TRT1.tr\",TRT 1\nhttps://example.org/trt.m3u8\n"
        source = {"id": "github-auto-8", "historical_source_only": True}
        text = normalize_original_source_text(source, raw)
        self.assertTrue(text.startswith("#EXTM3U\n#EXTINF"))
        self.assertEqual(len(list(entries(text))), 1)
        self.assertEqual(normalize_original_source_text({"id": "new"}, raw), raw)

    def test_invalid_ledger_rejected_not_silently_imported(self):
        orig = json.loads((ROOT / "history/run60-dynamic-source-ledger.json")
                          .read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "modified.json"
            orig["sources"][0]["url"] = "https://127.0.0.1/private.m3u"
            p.write_text(json.dumps(orig))
            with self.assertRaises(ValueError):
                load_original_run60_sources(p)

    def test_duplicate_original_identity_rejected(self):
        orig = json.loads((ROOT / "history/run60-dynamic-source-ledger.json")
                          .read_text(encoding="utf-8"))
        orig["sources"][1]["id"] = orig["sources"][0]["id"]
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "duplicated.json"
            p.write_text(json.dumps(orig))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_original_run60_sources(p)


if __name__ == "__main__":
    unittest.main()
