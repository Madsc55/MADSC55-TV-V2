#!/usr/bin/env python3
"""Offline fixtures for candidate completeness and provenance."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from discover import discover, entries, turkish_candidate, recognized_channel_ids
from source_integrity import verify

TR = '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",TRT 1\nhttps://example.org/trt.m3u8\n'
WORLD = '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",TRT One\nhttps://example.org/alternate.m3u8\n#EXTINF:-1 tvg-id="OTHER.us",News\nhttps://example.org/news.m3u8\n'
DUPLICATE = '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",TRT One\nhttps://example.org/alternate.m3u8\n'
LIVE = '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",TRT 1\nhttps://example.org/trt.m3u8\n'

class CandidateIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.sources = [("tr", TR), ("world", WORLD), ("duplicate", DUPLICATE)]
        self.scopes = {"tr": "TR", "world": "world", "duplicate": "world"}
        self.candidates = discover(self.sources, LIVE, self.scopes)

    def audit(self, candidates, errors=None):
        return verify(self.sources, LIVE, self.scopes, candidates, entries,
                      turkish_candidate, recognized_channel_ids(self.sources, self.scopes),
                      [], errors or [])

    def test_integrity_result_in_main_discovery(self):
        import inspect
        from discover import main
        body = inspect.getsource(main)
        self.assertIn("from source_integrity import verify", body)
        self.assertIn('result["source_integrity"] = integrity', body)
        self.assertIn('not integrity["verified"]', body)

    def test_exact_candidate_set(self):
        result = self.audit(self.candidates)
        self.assertTrue(result["verified"])
        self.assertEqual(result["expected_unique_new_candidates"], 1)
        self.assertEqual(result["missing_candidate_count"], 0)

    def test_duplicate_sources_preserve_provenance(self):
        self.assertEqual(set(self.candidates[0]["source_ids"]), {"world", "duplicate"})

    def test_missing_candidate_detected(self):
        result = self.audit([])
        self.assertFalse(result["verified"])
        self.assertEqual(result["missing_candidate_count"], 1)

    def test_missing_provenance_detected(self):
        modified = [{**self.candidates[0], "source_ids": ["world"]}]
        self.assertEqual(self.audit(modified)["provenance_mismatch_count"], 1)

    def test_failed_fetch_prevents_complete_status(self):
        self.assertFalse(self.audit(self.candidates, [{"source": "missing", "error": "TimeoutError"}])["verified"])

if __name__ == "__main__":
    unittest.main()
