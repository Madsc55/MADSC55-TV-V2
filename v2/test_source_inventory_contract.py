#!/usr/bin/env python3
"""Offline source inventory contract. No network, playlist edits, or playback."""
import json
import pathlib
import unittest
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "sources.json"
REQUIRED = {
    "iptv-org", "iptv-org-tr", "iptv-org-az",
    "iptv-org-tur-language", "iptv-org-aze-language",
    "free-tv-independent", "dearbulut-tr", "dearbulut-online",
    "dearbulut-all-candidates", "dearbulut-best-ranked",
    "turktv-itasli-archive", "onureroz-turk-index",
    "onureroz-turk-all", "onureroz-turk-karma",
    "onureroz-world-index",
}
class SourceInventoryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.sources = cls.config["sources"]

    def test_discovery_only(self):
        self.assertEqual(self.config["policy"], "discovery-only; never modify live playlist")

    def test_unique_identifiers_and_urls(self):
        ids = [s["id"] for s in self.sources]
        urls = [s["url"] for s in self.sources]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(urls), len(set(urls)))

    def test_https_public_source_urls(self):
        for source in self.sources:
            with self.subTest(source=source["id"]):
                parsed = urlsplit(source["url"])
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(parsed.hostname)
                self.assertIsNone(parsed.username)
                self.assertIsNone(parsed.password)
                self.assertFalse(parsed.fragment)
                self.assertIn(source["scope"], ("TR", "AZ", "SE", "world", "candidate"))

    def test_core_source_families_not_dropped(self):
        self.assertFalse(REQUIRED - {s["id"] for s in self.sources},
                         "Core discovery source disappeared from inventory")

    def test_global_online_feed_is_not_turkish_only(self):
        source = next(x for x in self.sources if x["id"] == "dearbulut-online")
        self.assertEqual(source["scope"], "world")

    def test_country_is_not_language_proof(self):
        from discover import turkish_candidate
        sample = {"name": "Unidentified Channel", "group": "", "tvg_id": ""}
        self.assertTrue(turkish_candidate(sample, "TR"))
        self.assertFalse(turkish_candidate(sample, "world"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
