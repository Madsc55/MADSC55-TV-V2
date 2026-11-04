#!/usr/bin/env python3
"""Offline integration regressions for bounded GitHub/Gist and GitLab/Codeberg sources."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import github_source_discovery as github
import run_forge_source_discovery as forge


class SourcePaginationCoverageTests(unittest.TestCase):
    def test_gitlab_keyset_finds_playlist_on_second_tree_page(self):
        requested = []
        def request(url):
            requested.append(url)
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main"}]
            if "/api/v4/projects/42/repository/tree?" in url:
                if "page_token=" in url:
                    return [{"type": "blob", "path": "az.m3u", "id": "file2"}]
                return [{"type": "blob", "path": "README.md", "id": "file1"} for _ in range(100)]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            raise AssertionError("Unexpected URL: " + url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["coverage_status"], "COMPLETE_QUERIES")
        self.assertTrue(any("pagination=keyset" in url for url in requested))
        self.assertTrue(any("page_token=file1" in url for url in requested))
        self.assertIn("az.m3u", result["sources"][0]["source_url"])

    def test_invalid_forge_tree_is_reported_not_silently_ignored(self):
        def request(url):
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main"}]
            if "/repository/tree" in url:
                return {"unexpected": True}
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            raise AssertionError(url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["coverage_status"], "PARTIAL_API_ERRORS")
        self.assertEqual(result["source_count"], 0)
        self.assertEqual(result["errors"][0]["error"], "ValueError")

    def test_github_first_page_and_per_repo_caps_report_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            config = pathlib.Path(temp) / "sources.json"
            report = pathlib.Path(temp) / "github.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            def api(url):
                if "/search/repositories?" in url:
                    return {"total_count": 90, "items": [
                        {"full_name": "sample/tv", "default_branch": "main"}]}
                if "/git/trees/" in url:
                    return {"tree": [{"type": "blob", "path": "tr%d.m3u" % x}
                                     for x in range(12)]}
                if "/users/sample/gists?" in url:
                    return [{"files": {"invalid.m3u": None}}]
                raise AssertionError(url)
            source = '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",TRT 1\nhttps://example.org/stream.m3u8\n'
            with patch.object(github, "CONFIG", config), \
                 patch.object(github, "OUT", report), \
                 patch.object(github, "QUERIES", ["tr tv"]), \
                 patch.object(github, "api", side_effect=api), \
                 patch.object(github, "fetch", return_value=source):
                github.main()
            output = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(output["coverage_status"], "PARTIAL_LIMITS")
            self.assertIn("GITHUB_SEARCH_FIRST_PAGE_LIMIT", output["limits_hit"])
            self.assertIn("GITHUB_REPO_PLAYLIST_FILE_LIMIT", output["limits_hit"])
            self.assertEqual(output["sources_found"], 8)
            self.assertEqual(output["errors"], [])
            self.assertFalse(output["playback_verified"])


    def test_github_first_page_uses_100_and_reports_incomplete_search(self):
        from urllib.parse import urlsplit, parse_qs
        with tempfile.TemporaryDirectory() as temp:
            config = pathlib.Path(temp) / "sources.json"
            report = pathlib.Path(temp) / "github.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            seen = []
            def api(url):
                seen.append(url)
                if "/search/repositories?" in url:
                    q = parse_qs(urlsplit(url).query)
                    self.assertEqual(q["per_page"], ["100"])
                    return {"total_count": 1, "incomplete_results": True,
                            "items": [{"full_name": "public/channel-list",
                                       "default_branch": "main", "size": 1}]}
                if "/git/trees/" in url:
                    return {"tree": []}
                if "/users/public/gists?" in url:
                    return []
                raise AssertionError(url)
            with patch.object(github, "CONFIG", config), \
                 patch.object(github, "OUT", report), \
                 patch.object(github, "QUERIES", ["turkish channels m3u"]), \
                 patch.object(github, "api", side_effect=api):
                github.main()
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["repositories_discovered"], 1)
            self.assertIn("GITHUB_SEARCH_INCOMPLETE_RESULTS", data["limits_hit"])
            self.assertEqual(data["coverage_status"], "PARTIAL_LIMITS")
            self.assertFalse(data["playback_verified"])

if __name__ == "__main__":
    unittest.main()
