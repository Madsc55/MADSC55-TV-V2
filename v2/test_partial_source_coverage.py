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
    def test_successful_source_candidates_still_deduplicate(self):
        sample = '#EXTM3U\n#EXTINF:-1 tvg-id="trt1.tr",TRT 1\nhttps://example.org/a.m3u8\n'
        candidates = discover.discover([("ok", sample)], "#EXTM3U\n", {"ok": "TR"})
        self.assertEqual(len(candidates), 1)
        self.assertNotIn("url", candidates[0])
        self.assertEqual(candidates[0]["source"], "ok")
if __name__ == "__main__":
    unittest.main(verbosity=2)
