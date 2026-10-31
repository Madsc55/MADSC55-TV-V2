#!/usr/bin/env python3
"""Offline regression for world-source alternatives linked to TR/AZ identities."""
import unittest
from discover import discover, recognized_channel_ids, entries, turkish_candidate

class CrossSourceArchiveParityTests(unittest.TestCase):
    def test_world_alternative_is_recognized_even_without_turkish_name(self):
        tr = '#EXTM3U\n#EXTINF:-1 tvg-id="ChannelXYZ",Kanal\nhttps://example.org/tr.m3u8\n'
        world = '#EXTM3U\n#EXTINF:-1 tvg-id="ChannelXYZ",News\nhttps://example.org/world.m3u8\n'
        sources = [("tr", tr), ("world", world)]
        scopes = {"tr": "TR", "world": "world"}
        ids = recognized_channel_ids(sources, scopes)
        self.assertIn("channelxyz", ids)
        entry = next(entries(world))
        self.assertFalse(turkish_candidate(entry, "world"))
        self.assertIn(entry["tvg_id"].casefold(), ids)
        candidates = discover(sources, "#EXTM3U\n", scopes)
        self.assertEqual(len(candidates), 2)
    def test_generic_world_news_not_promoted(self):
        world = '#EXTM3U\n#EXTINF:-1 tvg-id="News.Global",News\nhttps://example.org/world.m3u8\n'
        self.assertEqual(discover([("world", world)], "#EXTM3U\n", {"world": "world"}), [])
if __name__ == "__main__":
    unittest.main(verbosity=2)
