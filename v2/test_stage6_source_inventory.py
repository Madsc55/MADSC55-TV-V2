#!/usr/bin/env python3
"""Offline regression tests for the Stage 6 inventory preflight."""
import unittest
from stage6_source_inventory import evaluate

class Stage6InventoryTests(unittest.TestCase):
    def test_valid_sources_and_finished_dependencies(self):
        report = evaluate([
            {"id": "tr", "url": "https://example.org/tr.m3u", "scope": "TR"},
            {"id": "az", "url": "https://example.org/az.m3u", "scope": "AZ"},
            {"id": "world", "url": "https://example.org/world.m3u", "scope": "world"},
        ], [{"id": 33, "status": "completed"}, {"id": 34, "status": "pending"}])
        self.assertEqual(report["missing_required_scopes"], [])
        self.assertEqual(report["unfinished_predecessor_ids"], [])
        self.assertFalse(report["ffmpeg_video_audio_verified"])
        self.assertFalse(report["protected_ibo_modified"])

    def test_duplicate_invalid_and_unfinished(self):
        report = evaluate([
            {"id": "same", "url": "http://example.org/a", "scope": "TR"},
            {"id": "same", "url": "http://example.org/a", "scope": "TR"},
        ], [{"id": 33, "status": "pending"}, {"id": 34, "status": "pending"}])
        self.assertEqual(report["duplicate_source_ids"], ["same"])
        self.assertEqual(report["duplicate_active_urls"], ["http://example.org/a"])
        self.assertEqual(report["unfinished_predecessor_ids"], [33])
        self.assertEqual(report["missing_required_scopes"], ["AZ", "world"])
        self.assertEqual(report["invalid_https_source_ids"], ["same", "same"])

    def test_disabled_source_not_live(self):
        report = evaluate([
            {"id": "disabled", "url": "http://example.org", "scope": "TR", "enabled": False}
        ], [{"id": 34, "status": "pending"}])
        self.assertEqual(report["enabled_sources"], 0)
        self.assertEqual(report["invalid_https_source_ids"], [])

if __name__ == "__main__":
    unittest.main()
