#!/usr/bin/env python3
"""Grouped offline regression tests for source failover and loss protection."""
import tempfile
import unittest
from pathlib import Path
from source_failover import (
    SourceCache, FetchFailure, execute_pipeline, recover_source,
    validate_m3u, ALTERNATIVES,
)


class FailoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = SourceCache(Path(self.tmp.name))
        self.source = {"id": "iptv-org-region-south-america", "url": "https://example.org/primary.m3u"}

    def test_retry_then_fallback_preserves_source_identity(self):
        calls, delays = [], []
        def fetch(url):
            calls.append(url)
            if url == self.source["url"]:
                raise FetchFailure("TIMEOUT", True)
            return "#EXTM3U\n#EXTINF:-1,Real\nhttps://example.org/live.m3u8\n"
        content, audit = recover_source(self.source, self.cache, fetch, delays.append)
        self.assertEqual(audit["status"], "FALLBACK_OK")
        self.assertTrue(audit["fresh"])
        self.assertFalse(audit["upstream_source_identity_preserved"])
        self.assertEqual(delays, [2, 4, 8])
        self.assertEqual(calls[:4], [self.source["url"]] * 4)
        self.assertEqual(calls[4], ALTERNATIVES[self.source["id"]][0])
        self.assertIsNone(self.cache.get(self.source["id"]))

    def test_retired_ilyswch_source_is_not_relabelled_as_iptv_org(self):
        self.assertNotIn("ilyswch-iptv-tr", ALTERNATIVES)
        retired = {"id": "ilyswch-iptv-tr", "url": "https://example.org/deleted.m3u"}
        def fetch(_):
            raise FetchFailure("HTTP_404")
        content, audit = recover_source(retired, self.cache, fetch, lambda _: None)
        self.assertIsNone(content)
        self.assertEqual(audit["status"], "UNAVAILABLE")

    def test_failed_sources_use_cache_but_not_fresh(self):
        self.cache.set(self.source["id"], "#EXTM3U\n")
        def fail(url):
            raise FetchFailure("HTTP_404")
        content, audit = recover_source(self.source, self.cache, fail, lambda _: None)
        self.assertEqual(content, "#EXTM3U\n")
        self.assertEqual(audit["status"], "CACHE_RECOVERED")
        self.assertFalse(audit["fresh"])

    def test_corrupt_and_expired_cache_rejected(self):
        self.cache.set(self.source["id"], "#EXTM3U\n")
        data, meta = self.cache._paths(self.source["id"])
        data.write_text("corrupt", encoding="utf-8")
        self.assertIsNone(self.cache.get(self.source["id"]))
        self.cache.set(self.source["id"], "#EXTM3U\n")
        self.cache.max_age_seconds = 0.001
        import json
        record = json.loads(meta.read_text())
        record["timestamp"] = 1
        meta.write_text(json.dumps(record))
        self.assertIsNone(self.cache.get(self.source["id"]))

    def test_grouped_pipeline_continues_after_unavailable_source(self):
        good = {"id": "good", "url": "https://example.org/good.m3u"}
        def fetch(url):
            if "good.m3u" in url:
                return "#EXTM3U\n"
            raise FetchFailure("HTTP_404")
        results = execute_pipeline([self.source, good], self.cache, fetch, lambda _: None)
        self.assertEqual([r[2]["status"] for r in results], ["UNAVAILABLE", "PRIMARY_OK"])

    def test_cache_write_failure_does_not_discard_fresh_source(self):
        def broken_set(source_id, content):
            raise OSError("read-only cache")
        self.cache.set = broken_set
        def fetch(url):
            return "#EXTM3U\\n"
        content, audit = recover_source(self.source, self.cache, fetch, lambda _: None)
        self.assertEqual(content, "#EXTM3U\\n")
        self.assertTrue(audit["fresh"])
        self.assertEqual(audit["status"], "PRIMARY_OK")
        self.assertEqual(audit["failures"][0]["category"], "CACHE_WRITE_FAILED")

    def test_invalid_content_is_rejected(self):
        with self.assertRaises(FetchFailure):
            validate_m3u(b"<html>not a playlist</html>")



    def test_retry_backoff_does_not_cross_deadline(self):
        calls, sleeps = [], []
        def failing_fetch(url):
            calls.append(url)
            raise FetchFailure("HTTP_503", True)
        content, audit = recover_source(self.source, self.cache, failing_fetch,
            sleeps.append, deadline=1.0, clock=lambda: 0.0)
        self.assertIsNone(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, [])
        self.assertFalse(audit["fresh"])
        self.assertIn("RETRY_BUDGET_EXHAUSTED",
                      [row["category"] for row in audit["failures"]])

if __name__ == "__main__":
    unittest.main()
