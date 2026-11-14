import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from youtube_discovery import QUERIES, query_region, search, verify_detailed

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

    def test_verified_live_requires_actual_metadata(self):
        item = {"url": "https://www.youtube.com/watch?v=abcdefghijk"}
        cases = [
            ({"is_live": True}, ("LIVE_METADATA_VERIFIED", None)),
            ({"live_status": "is_live"}, ("LIVE_METADATA_VERIFIED", None)),
            ({"live_status": "was_live"}, ("NOT_CURRENTLY_LIVE", None)),
            ({}, ("UNVERIFIED", "LIVE_STATUS_MISSING")),
        ]
        for metadata, expected in cases:
            with self.subTest(metadata=metadata):
                result = verify_detailed(item, runner=lambda *a, **kw:
                                         SimpleNamespace(returncode=0, stdout=json.dumps(metadata), stderr=""))
                self.assertEqual(result, expected)

    def test_metadata_restrictions_do_not_claim_offline_video(self):
        item = {"url": "https://www.youtube.com/watch?v=abcdefghijk"}
        cases = [
            ("HTTP Error 429: too many requests", "UPSTREAM_RATE_LIMITED"),
            ("HTTP Error 403: Forbidden", "UPSTREAM_ACCESS_DENIED"),
            ("Sign in to confirm you're not a bot", "SIGN_IN_REQUIRED"),
            ("Video unavailable", "VIDEO_UNAVAILABLE"),
            ("Extractor error", "YTDLP_METADATA_FAILED"),
        ]
        for stderr, reason in cases:
            with self.subTest(stderr=stderr):
                status = verify_detailed(item, runner=lambda *a, **kw:
                                         SimpleNamespace(returncode=1, stdout="", stderr=stderr))
                self.assertEqual(status, ("UNVERIFIED", reason))
        self.assertEqual(verify_detailed(item, runner=lambda *a, **kw:
                         SimpleNamespace(returncode=0, stdout="[]", stderr="")),
                         ("UNVERIFIED", "INVALID_METADATA"))

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
