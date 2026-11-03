#!/usr/bin/env python3
"""Offline batch integration: GitHub/Gist + public GitLab/Codeberg source adapters."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import github_source_discovery as github
import run_forge_source_discovery as forge
from forge_source_review import approved_sources


class SourceAdapterIntegrationBatch(unittest.TestCase):
    def test_github_repository_and_public_gist_single_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            config = pathlib.Path(temp) / "sources.json"
            report = pathlib.Path(temp) / "github.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            called = []

            def api(url):
                called.append(url)
                if "/search/repositories?" in url:
                    return {"items": [{"full_name": "sample/tr-tv", "default_branch": "main"}]}
                if "/git/trees/" in url:
                    return {"tree": [{"type": "blob", "path": "channels.m3u"}]}
                if "/users/sample/gists?" in url:
                    return [{"files": {"az.m3u": {
                        "raw_url": "https://gist.githubusercontent.com/sample/abc/raw/az.m3u"
                    }}}]
                raise AssertionError("Unexpected GitHub API route")

            def fetch(url):
                self.assertIn(url.split("/")[2],
                              ("raw.githubusercontent.com", "gist.githubusercontent.com"))
                return '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",TRT 1\nhttps://example.org/live.m3u8\n'

            with patch.object(github, "CONFIG", config), \
                 patch.object(github, "OUT", report), \
                 patch.object(github, "QUERIES", ["turkish iptv"]), \
                 patch.object(github, "api", side_effect=api), \
                 patch.object(github, "fetch", side_effect=fetch):
                github.main()
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["sources_found"], 2)
            self.assertEqual(payload["errors"], [])
            self.assertEqual(payload["coverage_status"], "COMPLETE_QUERIES")
            self.assertFalse(payload["playback_verified"])
            self.assertTrue(any("/users/sample/gists?" in x for x in called))

    def test_forge_pagination_and_source_dedup(self):
        calls = []
        def request(url):
            calls.append(url)
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main"}] if "page=" not in url else []
            if "/api/v4/projects/42/repository/tree?" in url:
                return [{"type": "blob", "path": "tr.m3u"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": [{"owner": {"login": "sample"},
                                   "name": "tv", "default_branch": "main"}]}
            if "/api/v1/repos/sample/tv/git/trees/main" in url:
                return {"tree": [{"type": "blob", "path": "tr.m3u"}]}
            raise AssertionError("Unexpected forge route: " + url)
        report = forge.scan(request, terms=("turkish", "turkish"))
        self.assertEqual(report["source_count"], 2)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["coverage_status"], "COMPLETE_QUERIES")
        self.assertFalse(report["playback_verified"])
        self.assertEqual(sum("/repository/tree?" in x for x in calls), 1)
        self.assertEqual(approved_sources(report, set()), [])

    def test_partial_forge_failure_visible_without_silent_success(self):
        def request(url):
            if "gitlab.com" in url:
                raise OSError("unreachable")
            if "/repos/search" in url:
                return {"data": []}
            raise AssertionError(url)
        report = forge.scan(request, terms=("iptv",))
        self.assertEqual(report["coverage_status"], "PARTIAL_API_ERRORS")
        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["source_count"], 0)
        self.assertFalse(report["playback_verified"])


if __name__ == "__main__":
    unittest.main()
