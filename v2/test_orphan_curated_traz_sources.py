#!/usr/bin/env python3
"""Offline fail-closed tests for two pinned candidate-only M3U sources."""
import unittest
from unittest.mock import patch

from orphan_curated_traz_sources import (
    pinned_traz_candidate_references, PINNED_REVISION,
)

class PinnedTRAZSourceTests(unittest.TestCase):
    def test_two_distinct_pinned_traz_sources_without_av_promotion(self):
        refs = pinned_traz_candidate_references()
        self.assertEqual(len(refs), 2)
        self.assertEqual({r["scope"] for r in refs}, {"TR", "AZ"})
        self.assertTrue(all(PINNED_REVISION in r["url"] for r in refs))
        self.assertTrue(all(r["url"].startswith("https://raw.githubusercontent.com/")
                            for r in refs))
        self.assertTrue(all(r["origin"] == "orphan-discovery-reference" for r in refs))
        self.assertTrue(all(r["playback_verified"] is False for r in refs))
        self.assertTrue(all(r["ibo_playlist_modified"] is False for r in refs))

    def test_dedupe_existing_reference_and_preserve_other(self):
        first, second = pinned_traz_candidate_references()
        self.assertEqual(pinned_traz_candidate_references(
            known_urls={first["url"]}), [second])
        self.assertEqual(pinned_traz_candidate_references(
            known_urls={first["url"], second["url"]}), [])

    def test_identity_collision_rejected(self):
        first = pinned_traz_candidate_references()[0]
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            pinned_traz_candidate_references(known_ids={first["id"]})

    def test_untrusted_source_validator_failure_prevents_promotion(self):
        with patch("orphan_curated_traz_sources.safe_reference_url",return_value=False):
            with self.assertRaisesRegex(ValueError, "Unapproved"):
                pinned_traz_candidate_references()

if __name__ == "__main__":
    unittest.main()
