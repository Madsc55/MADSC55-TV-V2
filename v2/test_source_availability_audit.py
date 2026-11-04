#!/usr/bin/env python3
import unittest
from unittest.mock import patch
import io
from source_availability_audit import audit, probe, active_source_inventory

class SourceAvailabilityTests(unittest.TestCase):
    def test_probe_rejects_html_even_with_http_200(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b"<html>not a playlist</html>"
        with patch("source_availability_audit.urllib.request.build_opener") as opener, \
             patch("source_availability_audit.time.sleep"):
            opener.return_value.open.return_value = Response()
            result = probe("https://example.org/playlist.m3u")
        self.assertEqual(result["status"], "INVALID_M3U")
        self.assertFalse(result["sample_m3u_header"])

    def test_http_200_non_m3u_transient_response_is_retried_but_not_accepted_without_header(self):
        class Response:
            status = 200
            def __init__(self, content): self.content = content
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return self.content
        with patch("source_availability_audit.urllib.request.build_opener") as opener, \
             patch("source_availability_audit.time.sleep") as sleep:
            opener.return_value.open.side_effect = [
                Response(b"<html>temporary page</html>"),
                Response(b"#EXTM3U\\n#EXTINF:-1,T\\nhttps://example.org/live.m3u8")]
            result = probe("https://example.org/list.m3u")
            self.assertEqual(result["status"], "HTTP_OK")
            self.assertEqual(opener.return_value.open.call_count, 2)
            self.assertEqual(sleep.call_count, 1)
        with patch("source_availability_audit.urllib.request.build_opener") as opener, \
             patch("source_availability_audit.time.sleep") as sleep:
            opener.return_value.open.return_value = Response(b"<html>persistent failure</html>")
            result = probe("https://example.org/list.m3u")
            self.assertEqual(result["status"], "INVALID_M3U")
            self.assertEqual(result["http_status"], 200)
            self.assertEqual(result["invalid_m3u_retry_attempts"], 2)
            self.assertEqual(opener.return_value.open.call_count, 3)
            self.assertEqual(sleep.call_count, 2)

    def test_probe_accepts_bom_and_whitespace_m3u_header(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b"\xef\xbb\xbf\n#EXTM3U\n"
        with patch("source_availability_audit.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response()
            result = probe("https://example.org/playlist.m3u")
        self.assertEqual(result["status"], "HTTP_OK")

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
    def test_retired_historical_source_not_counted_as_active_unavailable(self):
        rows = [
            {"id": "active", "url": "https://example.org/tr.m3u"},
            {"id": "retired", "url": "https://example.org/missing.m3u",
             "enabled": False},
        ]
        active, disabled = active_source_inventory(rows)
        self.assertEqual([x["id"] for x in active], ["active"])
        self.assertEqual(disabled, ["retired"])
        outcome = audit(active, lambda _: {"status": "HTTP_OK"})
        self.assertEqual(outcome["source_count"], 1)
        self.assertEqual(outcome["coverage_status"], "COMPLETE")
        self.assertFalse(outcome["playback_verified"])

    def test_error_kept_per_source(self):
        report = audit([{"id": "missing", "url": "https://example.org/a.m3u"}],
                       lambda url: {"status": "HTTP_ERROR", "http_status": 404})
        self.assertEqual(report["results"][0]["http_status"], 404)
        self.assertEqual(report["coverage_status"], "NO_SOURCES_REACHABLE")
        self.assertEqual(report["unreachable_source_count"], 1)
    def test_empty_inventory_not_complete(self):
        report = audit([], lambda url: self.fail("unexpected probe"))
        self.assertEqual(report["coverage_status"], "NO_CONFIGURED_SOURCES")
    def test_mixed_source_status_is_partial(self):
        sources = [{"id": "ok", "url": "https://example.org/a.m3u"},
                   {"id": "bad", "url": "https://example.org/b.m3u"}]
        report = audit(sources, lambda url: {"status": "HTTP_OK"} if url.endswith("a.m3u") else {"status": "FETCH_ERROR"})
        self.assertEqual(report["coverage_status"], "PARTIAL_SOURCE_AVAILABILITY")

    def test_transient_http_503_is_rechecked_but_403_is_reported(self):
        from urllib.error import HTTPError
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b"#EXTM3U\n"
        with patch("source_availability_audit.urllib.request.build_opener") as opener, \
             patch("source_availability_audit.time.sleep") as sleep:
            opener.return_value.open.side_effect = [
                HTTPError("https://example.org/a.m3u", 503, "temporary", {}, None),
                Response()]
            result = probe("https://example.org/a.m3u")
            self.assertEqual(result["status"], "HTTP_OK")
            self.assertEqual(opener.return_value.open.call_count, 2)
            self.assertEqual(sleep.call_count, 1)
        with patch("source_availability_audit.urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(
                "https://example.org/a.m3u", 403, "forbidden", {}, None)
            result = probe("https://example.org/a.m3u")
            self.assertEqual(result, {"status": "HTTP_ERROR", "http_status": 403})
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_unsafe_redirect_not_retried(self):
        with patch("source_availability_audit.urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = ValueError("Unsafe source redirect")
            result = probe("https://example.org/a.m3u")
            self.assertEqual(result, {"status": "FETCH_ERROR", "error": "ValueError"})
            self.assertEqual(opener.return_value.open.call_count, 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
