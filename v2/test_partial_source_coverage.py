#!/usr/bin/env python3
"""Offline regressions for partial source scans and independent forge API outages."""
import unittest
from unittest.mock import patch
import run_forge_source_discovery as forge
import discover

class PartialCoverageTests(unittest.TestCase):
    def test_forge_api_outage_retains_error_report(self):
        with patch.object(forge, "TERMS", ["turkish iptv"]), \
             patch.object(forge, "api_json", side_effect=OSError("unavailable")):
            report = forge.scan()
        self.assertEqual(report["coverage_status"], "PARTIAL_API_ERRORS")
        self.assertEqual(len(report["errors"]), 2)
        self.assertEqual(report["sources"], [])
    def test_forge_project_page_limit_is_reported(self):
        from forge_source_discovery import GITLAB_API
        projects = [{"id": i, "branch": "main"} for i in range(12)]
        def fake_api(url):
            if url.startswith(GITLAB_API) and "/repository/tree" not in url:
                return projects
            return []
        with patch.object(forge, "TERMS", ["iptv"]), \
             patch.object(forge, "gitlab_projects", return_value=projects), \
             patch.object(forge, "codeberg_projects", return_value=[]), \
             patch.object(forge, "api_json", side_effect=fake_api):
            report = forge.scan()
        self.assertEqual(report["coverage_status"], "PARTIAL_LIMITS")
        self.assertIn("GITLAB_PROJECT_PAGE_LIMIT", report["limits_hit"])
    def test_gitlab_tree_pagination_fetches_second_page(self):
        from forge_source_discovery import GITLAB_API
        calls = []
        def fake_api(url):
            calls.append(url)
            if "/repository/tree" in url:
                if "page=2" in url:
                    return [{"type": "blob", "path": "channels.m3u"}]
                return [{"type": "blob", "path": "other.txt"}] * 100
            if url.startswith(GITLAB_API):
                return [{"id": 1, "default_branch": "main"}]
            return {"data": []}
        with patch.object(forge, "TERMS", ["iptv"]), \
             patch.object(forge, "api_json", side_effect=fake_api):
            report = forge.scan()
        self.assertTrue(any("page=2" in url for url in calls))
        self.assertEqual(len(report["sources"]), 1)
        self.assertEqual(report["coverage_status"], "COMPLETE_QUERIES")
    def test_forge_playlist_path_cap_is_visible(self):
        from forge_source_discovery import GITLAB_API, MAX_PATHS
        def fake_api(url):
            if "/repository/tree" in url:
                return [{"type": "blob", "path": "channels" + str(i) + ".m3u"} for i in range(MAX_PATHS + 1)]
            if url.startswith(GITLAB_API):
                return [{"id": 1, "default_branch": "main"}]
            return {"data": []}
        with patch.object(forge, "TERMS", ["iptv"]), \
             patch.object(forge, "api_json", side_effect=fake_api):
            report = forge.scan()
        self.assertEqual(report["coverage_status"], "PARTIAL_LIMITS")
        self.assertIn("GITLAB_PLAYLIST_PATH_LIMIT", report["limits_hit"])
        self.assertEqual(len(report["sources"]), MAX_PATHS)
    def test_successful_source_candidates_still_deduplicate(self):
        sample = '#EXTM3U\n#EXTINF:-1 tvg-id="trt1.tr",TRT 1\nhttps://example.org/a.m3u8\n'
        candidates = discover.discover([("ok", sample)], "#EXTM3U\n", {"ok": "TR"})
        self.assertEqual(len(candidates), 1)
        self.assertNotIn("url", candidates[0])
        self.assertEqual(candidates[0]["source"], "ok")
if __name__ == "__main__":
    unittest.main(verbosity=2)
