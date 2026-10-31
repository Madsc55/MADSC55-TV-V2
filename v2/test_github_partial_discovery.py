#!/usr/bin/env python3
"""GitHub/Gist discovery retains partial audit on API outages, without network."""
import json
import tempfile
import pathlib
import unittest
from unittest.mock import patch
import github_source_discovery as discovery

class GitHubPartialTests(unittest.TestCase):
    def test_api_failure_is_recorded_without_dropping_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / "sources.json"
            report = root / "report.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            with patch.object(discovery, "CONFIG", config), \
                 patch.object(discovery, "OUT", report), \
                 patch.object(discovery, "QUERIES", ["turkish iptv m3u"]), \
                 patch.object(discovery, "api", side_effect=OSError("rate limit")):
                discovery.main()
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["coverage_status"], "PARTIAL_API_ERRORS")
            self.assertEqual(len(payload["errors"]), 1)
            self.assertEqual(payload["sources_found"], 0)
            self.assertIs(payload["playback_verified"], False)
            self.assertNotIn("rate limit", report.read_text(encoding="utf-8"))
    def test_repo_limit_is_reported_as_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / "sources.json"
            report = root / "report.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            def fake_api(url):
                if "/search/repositories?" in url:
                    return {"items": [{"full_name": "owner/a", "default_branch": "main"},
                                      {"full_name": "owner/b", "default_branch": "main"}]}
                return {"tree": []}
            with patch.object(discovery, "CONFIG", config), \
                 patch.object(discovery, "OUT", report), \
                 patch.object(discovery, "QUERIES", ["turkish iptv m3u"]), \
                 patch.object(discovery, "MAX_REPOS", 1), \
                 patch.object(discovery, "api", side_effect=fake_api):
                discovery.main()
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["coverage_status"], "PARTIAL_LIMITS")
            self.assertIn("MAX_REPOS", payload["limits_hit"])
    def test_truncated_tree_is_reported_as_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / "sources.json"
            report = root / "report.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            def fake_api(url):
                if "/search/repositories?" in url:
                    return {"items": [{"full_name": "owner/a", "default_branch": "main"}]}
                return {"tree": [], "truncated": True}
            with patch.object(discovery, "CONFIG", config), \
                 patch.object(discovery, "OUT", report), \
                 patch.object(discovery, "QUERIES", ["turkish iptv m3u"]), \
                 patch.object(discovery, "api", side_effect=fake_api):
                discovery.main()
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["coverage_status"], "PARTIAL_LIMITS")
            self.assertIn("TRUNCATED_GITHUB_TREE", payload["limits_hit"])
if __name__ == "__main__":
    unittest.main(verbosity=2)
