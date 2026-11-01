#!/usr/bin/env python3
"""Offline regression tests for Turkish/Azerbaijani candidate discovery."""
import unittest
from discover import discover, turkish_candidate


def entry(name, group="", tvg_id=""):
    return {"name": name, "group": group, "tvg_id": tvg_id, "logo": ""}


class DiscoveryMetadataTests(unittest.TestCase):
    def test_world_metadata_hints(self):
        for name, group, tvg_id in (
            ("Diaspora TV", "TR", ""),
            ("Diaspora TV", "[AZ]", ""),
            ("Diaspora TV", "AZE", ""),
            ("Diaspora TV", "", "station.tr"),
            ("Türkçe Haber", "", ""),
            ("Azerice Haber", "", ""),
        ):
            with self.subTest(name=name, group=group, tvg_id=tvg_id):
                self.assertTrue(turkish_candidate(entry(name, group, tvg_id), "world"))

    def test_unrelated_world_channel_is_not_accepted(self):
        self.assertFalse(turkish_candidate(entry("Unrelated Music", "World", "music.us"), "world"))

    def test_source_provenance_is_preserved(self):
        source = "#EXTM3U\n#EXTINF:-1 group-title=\"TR\",Example TR\nhttps://example.org/live.m3u8\n"
        result = discover([("one", source), ("two", source)], "#EXTM3U\n", {"one": "TR", "two": "TR"})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_ids"], ["one", "two"])


if __name__ == "__main__":
    unittest.main()
