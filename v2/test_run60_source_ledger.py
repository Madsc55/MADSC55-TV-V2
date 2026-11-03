#!/usr/bin/env python3
"""One-batch original dynamic source identity proof and safety regressions."""
import json
from pathlib import Path
import tempfile
import unittest
from run60_source_ledger import read_verified_ledger, inventory_coverage


class HistoricalDynamicSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        self.ledger = d / "ledger.json"
        self.snapshot = d / "snapshot.json"
        self.url = "https://raw.githubusercontent.com/example/iptv/main/tr.m3u"
        self.original = {"schema": 1, "source_run_id": 40743765437,
                         "artifact_id": 12840886350, "sources": [
                             {"id": "github-auto-0", "url": self.url,
                              "kind": "m3u", "original_entries": 10,
                              "run60_tested": 9, "old_only": 8}]}
        self.snap = {"sources": [{"url": self.url, "entries": 10}]}
        self.history = {"source_breakdown": [
            {"source_id": "github-auto-0", "old_tested": 9,
             "old_only_url_identities": 8}]}

    def write(self):
        self.ledger.write_text(json.dumps(self.original))
        self.snapshot.write_text(json.dumps(self.snap))

    def load(self):
        return read_verified_ledger(self.ledger, self.snapshot, self.history,
                                    expected_sources=1, expected_old_only=8)

    def test_original_order_and_exact_url_success(self):
        self.write()
        sources = self.load()
        self.assertEqual([s["id"] for s in sources], ["github-auto-0"])
        self.assertTrue(sources[0]["historical_source_only"])

    def test_fake_or_changed_source_url_rejected(self):
        self.original["sources"][0]["url"] = "https://raw.githubusercontent.com/other/fake/main/tr.m3u"
        self.write()
        with self.assertRaisesRegex(ValueError, "not backed"):
            self.load()

    def test_missing_original_entry_rejected(self):
        self.original["sources"][0]["run60_tested"] = 10
        self.write()
        with self.assertRaises(ValueError):
            self.load()

    def test_untrusted_host_rejected_even_when_original_snapshot_matches(self):
        self.url = "https://127.0.0.1/private.m3u"
        self.original["sources"][0]["url"] = self.url
        self.snap["sources"][0]["url"] = self.url
        self.write()
        with self.assertRaisesRegex(ValueError, "Untrusted"):
            self.load()

    def test_catalog_mapping_and_live_read_are_separate_claims(self):
        supplemental = [{"source_id": "github-auto-0",
                         "status": "SOURCE_CONTENT_FAILED"}]
        result = inventory_coverage(self.history, [], supplemental)
        self.assertEqual(result["recovered_exact_original_source_locations"], 1)
        self.assertFalse(result["all_original_feeds_fully_parsed_now"])
        supplemental[0]["status"] = "PARSED_M3U_NOT_PLAYBACK_VERIFIED"
        result = inventory_coverage(self.history, [], supplemental)
        self.assertTrue(result["all_original_feeds_fully_parsed_now"])
        self.assertFalse(result["playback_reverified"])

    def test_missing_source_mapping_is_not_silently_complete(self):
        result = inventory_coverage(self.history, [], [])
        self.assertEqual(result["unmapped_source_ids"], ["github-auto-0"])
        self.assertFalse(result["all_original_locations_recovered"])


if __name__ == "__main__":
    unittest.main()
