#!/usr/bin/env python3
import unittest
from source_availability_audit import audit

class SourceAvailabilityTests(unittest.TestCase):
    def test_metadata_only(self):
        sources = [{"id": "tr", "url": "https://example.org/tr.m3u", "scope": "TR"},
                   {"id": "world", "url": "https://example.org/world.m3u", "scope": "world"}]
        calls = []
        def fake(url):
            calls.append(url)
            return {"status": "HTTP_OK", "http_status": 200, "sample_m3u_header": True}
        report = audit(sources, fake)
        self.assertEqual(len(calls), 2)
        self.assertEqual(report["source_count"], 2)
        self.assertEqual(report["coverage_status"], "COMPLETE")
        self.assertEqual(report["reachable_source_count"], 2)
        self.assertFalse(report["playback_verified"])
        self.assertNotIn("url", report["results"][0])
    def test_error_kept_per_source(self):
        report = audit([{"id": "missing", "url": "https://example.org/a.m3u"}],
                       lambda url: {"status": "HTTP_ERROR", "http_status": 404})
        self.assertEqual(report["results"][0]["http_status"], 404)
        self.assertEqual(report["coverage_status"], "PARTIAL_SOURCE_AVAILABILITY")
        self.assertEqual(report["unreachable_source_count"], 1)
if __name__ == "__main__":
    unittest.main(verbosity=2)
