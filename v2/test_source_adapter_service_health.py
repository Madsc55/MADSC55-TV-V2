#!/usr/bin/env python3
"""Source-only health integration tests: no network, M3U playback or mutations."""
import unittest
from unittest.mock import patch
from source_adapter_service_health import SOURCES, audit, probe, safe_source_url


class SourceAdapterServiceHealthTests(unittest.TestCase):
    def test_known_services_are_public_https(self):
        self.assertEqual(len({s["id"] for s in SOURCES}), len(SOURCES))
        self.assertEqual({s["type"] for s in SOURCES},
                         {"m3u", "github", "gist", "gitlab", "codeberg"})
        self.assertTrue(all(safe_source_url(s["url"]) for s in SOURCES))

    def test_no_private_urls_before_any_network(self):
        with patch("urllib.request.build_opener", side_effect=AssertionError("network")):
            for url in ("http://api.github.com/gists", "https://localhost/a.m3u",
                        "https://127.0.0.1/a.m3u", "https://user:pass@gitlab.com/api/v4/projects",
                        "https://codeberg.org:8443/api/v1/repos/search"):
                with self.subTest(url=url):
                    self.assertEqual(probe({"url": url, "type": "gist"})["status"],
                                     "INVALID_SOURCE_URL")

    def test_bulk_health_is_audited_without_claiming_playback(self):
        def check(source):
            return {"status": "AVAILABLE" if source["type"] == "m3u" else "HTTP_ERROR",
                    "http_status": 429 if source["type"] != "m3u" else 200}
        report = audit(check=check)
        self.assertEqual(report["checked"], len(SOURCES))
        self.assertEqual(report["available"], 2)
        self.assertEqual(report["coverage_status"], "PARTIAL")
        self.assertEqual(report["streams_scanned"], 0)
        self.assertFalse(report["playlist_modified"])
        self.assertFalse(report["playback_verified"])


if __name__ == "__main__":
    unittest.main()
