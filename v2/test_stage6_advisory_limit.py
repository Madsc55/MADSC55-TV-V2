#!/usr/bin/env python3
"""Ensure large worldwide candidate batches cannot crash advisory linkage."""
import unittest
from advisory_channel_identity_bridge import link_or_defer

class Stage6AdvisoryLimitTests(unittest.TestCase):
    def test_oversized_batch_is_preserved_without_metadata_proof(self):
        candidates = [{}, {}, {}]
        result = link_or_defer(candidates, "missing.json", "missing.json", max_candidates=2)
        self.assertEqual(result["status"], "DEFERRED_TOO_MANY_CANDIDATES")
        self.assertEqual(result["candidate_count"], 3)
        self.assertEqual(len(candidates), 3)
        self.assertFalse(result["av_verified"])
        self.assertFalse(result["main_playlist_modified"])

    def test_invalid_candidate_input_fails_closed(self):
        with self.assertRaises(ValueError):
            link_or_defer(None, "missing.json", "missing.json", max_candidates=2)

if __name__ == "__main__":
    unittest.main()
