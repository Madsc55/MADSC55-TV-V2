#!/usr/bin/env python3
"""Batch-test both forge API adapters without network access."""
import unittest
from urllib.parse import urlsplit
from forge_source_runner import scan, api_json

class ForgeRunnerTests(unittest.TestCase):
    def test_gitlab_and_codeberg_end_to_end(self):
        def fake(url):
            p = urlsplit(url)
            if p.path == "/api/v4/projects":
                return [{"id": 42, "default_branch": "main"}]
            if p.path == "/api/v4/projects/42/repository/tree":
                return [{"type": "blob", "path": "tr.m3u"}]
            if p.path == "/api/v1/repos/search":
                return {"data": [{"owner": {"login": "sample"}, "name": "tv", "default_branch": "main"}]}
            if p.path == "/api/v1/repos/sample/tv/git/trees/main":
                return {"tree": [{"type": "blob", "path": "az.m3u8"}]}
            raise AssertionError("Unexpected API endpoint: " + p.path)
        result = scan(fake, terms=("iptv", "iptv"))
        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["errors"], [])
        self.assertEqual({x["forge"] for x in result["sources"]}, {"gitlab", "codeberg"})
        self.assertFalse(result["playback_verified"])

    def test_partial_api_failure_does_not_hide_success(self):
        def fake(url):
            if "gitlab.com" in url:
                raise OSError("offline")
            if "/repos/search" in url:
                return {"data": []}
            return {}
        result = scan(fake, terms=("iptv",))
        self.assertEqual(result["coverage_status"], "PARTIAL_API_ERRORS")
        self.assertEqual(len(result["errors"]), 1)

    def test_untrusted_api_host_rejected(self):
        with self.assertRaises(ValueError):
            api_json("https://127.0.0.1/private")

if __name__ == "__main__":
    unittest.main()
