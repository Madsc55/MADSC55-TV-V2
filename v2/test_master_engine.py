#!/usr/bin/env python3
"""Offline integration tests for the master engine. No mocked success reports."""
import unittest
from master_engine import build

class MasterTests(unittest.TestCase):
    def test_real_parser_dedup_history_and_provenance(self):
        live = "#EXTM3U\n#EXTINF:-1,Existing\nhttps://example.org/existing.m3u8\n"
        data = "#EXTM3U\n#EXTINF:-1 tvg-id=\"TRT1.tr\",TRT 1\nhttps://example.org/new.m3u8\n#EXTINF:-1,Existing\nhttps://example.org/existing.m3u8\n"
        sources = [({"id": "a", "scope": "TR"}, data), ({"id": "b", "scope": "TR"}, data)]
        history = [{"url": "https://example.org/new.m3u8", "source": "#60"},
                   {"anonymous_id": "missing-real-url"}]
        items, audit, report = build(sources, live, history, checker=lambda item: True)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_ids"], ["a", "b"])
        self.assertEqual(items[0]["network_status"], "HLS_MANIFEST_REACHABLE")
        self.assertFalse(items[0]["device_verified"])
        self.assertEqual(len(items[0]["history"]), 1)
        self.assertEqual(report["historical_missing_real_url"], 1)
        self.assertEqual([x["parsed"] for x in audit], [2, 2])
    def test_invalid_m3u_is_not_accepted(self):
        items, audit, _ = build([({"id": "html", "scope": "TR"}, "<html>not a playlist</html>")], "#EXTM3U\n")
        self.assertEqual(items, [])
        self.assertEqual(audit[0]["status"], "INVALID_M3U")

    def test_checker_exception_does_not_abort_scan(self):
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        def fail(_):
            raise TimeoutError("stream timeout")
        items, _, _ = build([({"id": "tr", "scope": "TR"}, data)], "#EXTM3U\n", checker=fail)
        self.assertEqual(items[0]["network_status"], "UNKNOWN_OR_FAILED")
        self.assertFalse(items[0]["device_verified"])

    def test_no_device_success_inference(self):
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        items, _, _ = build([({"id": "tr", "scope": "TR"}, data)], "#EXTM3U\n",
                            checker=lambda item: False)
        self.assertEqual(items[0]["network_status"], "UNKNOWN_OR_FAILED")
        self.assertFalse(items[0]["device_verified"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
