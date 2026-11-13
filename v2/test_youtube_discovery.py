import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from youtube_discovery import QUERIES, query_region, search

class WorldwideYouTubeDiscoveryTests(unittest.TestCase):
    def test_query_set_includes_world_regions_and_languages(self):
        self.assertGreaterEqual(len(QUERIES), 30)
        joined = " ".join(QUERIES).casefold()
        for term in ("african", "asian", "european", "latin american",
                     "arabic", "hindi", "spanish", "french", "portuguese",
                     "japanese korean"):
            self.assertIn(term, joined)

    def test_region_mapping_preserves_tr_az_and_world(self):
        self.assertEqual(query_region("Türkiye televizyon canlı yayın resmi"), "TR")
        self.assertEqual(query_region("Azərbaycan TV live yayım"), "AZ")
        self.assertEqual(query_region("African television live stream official"), "WORLD")

    def test_search_results_carry_region_tag(self):
        payload = {"entries": [{"id": "abcdefghijk", "title": "Live News",
                                "channel": "World News"}]}
        with patch("youtube_discovery.subprocess.run",
                   return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")):
            rows, error = search("official international news TV live stream")
        self.assertIsNone(error)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["region"], "WORLD")
        self.assertEqual(rows[0]["status"], "DISCOVERED_NOT_LIVE_VERIFIED")

if __name__ == "__main__":
    unittest.main()
