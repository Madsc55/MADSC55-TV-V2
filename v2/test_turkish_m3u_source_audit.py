#!/usr/bin/env python3
"""Grouped source-only and genuine historical URL loss audit regressions."""
import hashlib
import unittest

from turkish_m3u_source_audit import audit_endpoints, safe_probing_result


class TurkishSourceAuditTests(unittest.TestCase):
    def test_all_sources_retained_with_stable_order_and_no_plaintext_urls(self):
        sources = [{"id": "iptv-tr", "url": "https://example.org/TR.m3u?token=SECRET",
                    "scope": "TR", "kind": "m3u"},
                   {"id": "world", "url": "https://example.org/world.m3u",
                    "scope": "world", "kind": "m3u"}]
        output = audit_endpoints(sources, lambda url: {"status": "HTTP_OK"}
                                 if "/TR.m3u" in url else {"status": "HTTP_ERROR",
                                                         "http_status": 404}, workers=2)
        self.assertEqual(output["configured_sources"], 2)
        self.assertEqual(output["source_headers_reachable"], 1)
        self.assertEqual(output["status"], "PARTIAL_SOURCE_HEADERS")
        self.assertEqual([s["source_id"] for s in output["sources"]],
                         ["iptv-tr", "world"])
        self.assertNotIn("SECRET", str(output))
        self.assertEqual(output["media_streams_probed"], 0)

    def test_retired_upstream_is_preserved_without_fetching(self):
        rows = [
            {"id": "retired", "url": "https://example.org/old.m3u", "enabled": False,
             "retirement_reason": "UPSTREAM_REPOSITORY_NO_LONGER_CONTAINS_M3U_2026_11_03"},
            {"id": "active", "url": "https://example.org/active.m3u"},
        ]
        checked = []
        def checker(url):
            checked.append(url)
            return {"status": "HTTP_OK"}
        result = audit_endpoints(rows, checker)
        self.assertEqual(len(checked), 1)
        self.assertEqual(result["retired_historical_sources"], 1)
        self.assertEqual(result["active_sources"], 1)
        self.assertEqual(result["source_headers_unreachable"], 0)
        self.assertEqual(result["status"], "ACTIVE_SOURCE_HEADERS_REACHABLE")
        self.assertEqual(result["sources"][0]["status"], "DISABLED_UPSTREAM_REMOVED")

    def test_source_exception_does_not_erase_remaining_sources(self):
        sources = [{"id": "one", "url": "https://example.org/one.m3u"},
                   {"id": "two", "url": "https://example.org/two.m3u"}]
        def checker(url):
            if "one" in url:
                raise TimeoutError("query-token-not-for-logs")
            return {"status": "HTTP_OK"}
        result = audit_endpoints(sources, checker)
        self.assertEqual(result["status_counts"], {"FETCH_ERROR": 1, "HTTP_OK": 1})
        self.assertNotIn("query-token-not-for-logs", str(result))

    def test_empty_or_duplicate_config_fails_closed(self):
        with self.assertRaises(ValueError):
            audit_endpoints([], lambda _: {"status": "HTTP_OK"})
        with self.assertRaises(ValueError):
            audit_endpoints([{"id": "same", "url": "https://a.example.org/a.m3u"},
                             {"id": "same", "url": "https://a.example.org/b.m3u"}],
                            lambda _: {"status": "HTTP_OK"})

    def test_only_explicit_audit_status_and_http_code_are_reported(self):
        result = safe_probing_result(
            {"id": "tr", "url": "https://example.org/token=PRIVATE", "scope": "TR"},
            lambda _: {"status": "HTTP_OK", "http_status": 200,
                       "url": "https://example.org/private", "body": "SECRET"})
        self.assertEqual(result["source_id"], "tr")
        self.assertNotIn("SECRET", str(result))
        self.assertNotIn("private", str(result).lower())
        self.assertEqual(result["source_url_sha256"],
                         hashlib.sha256(b"https://example.org/token=PRIVATE").hexdigest())


if __name__ == "__main__":
    unittest.main()
