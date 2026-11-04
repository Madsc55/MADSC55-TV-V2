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
                return [{"id": 42, "default_branch": "main"}] if "&page=" not in url else []
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


    def test_github_does_not_request_confirmed_empty_repository_trees(self):
        with tempfile.TemporaryDirectory() as temp:
            config = pathlib.Path(temp) / "sources.json"
            report = pathlib.Path(temp) / "github.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            called = []
            def api(url):
                called.append(url)
                if "/search/repositories?" in url:
                    return {"items": [{"full_name": "sample/empty",
                                       "default_branch": "main", "size": 0}]}
                raise AssertionError("Empty repository must not be scanned: " + url)
            with patch.object(github, "CONFIG", config), \
                 patch.object(github, "OUT", report), \
                 patch.object(github, "QUERIES", ["turkish iptv"]), \
                 patch.object(github, "api", side_effect=api):
                github.main()
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["skipped_metadata_proven_empty_or_disabled_repositories"], 1)
            self.assertEqual(payload["sources_found"], 0)
            self.assertEqual(payload["errors"], [])
            self.assertTrue(all("/git/trees/" not in url for url in called))

    def test_gist_rate_limit_keeps_unvisited_owners_explicit(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as temp:
            config = pathlib.Path(temp) / "sources.json"
            report = pathlib.Path(temp) / "github.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            calls = []
            def api(url):
                calls.append(url)
                if "/search/repositories?" in url:
                    return {"items": [
                        {"full_name": "alpha/channels", "default_branch": "main", "size": 1},
                        {"full_name": "beta/channels", "default_branch": "main", "size": 1}]}
                if "/git/trees/" in url:
                    return {"tree": []}
                if "/users/alpha/gists?" in url:
                    raise HTTPError(url, 403, "rate limit", {"X-RateLimit-Remaining": "0"}, None)
                raise AssertionError("No more Gist requests after exhausted budget: " + url)
            with patch.object(github, "CONFIG", config), \
                 patch.object(github, "OUT", report), \
                 patch.object(github, "QUERIES", ["turkish iptv"]), \
                 patch.object(github, "api", side_effect=api):
                github.main()
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["gist_owners_unchecked_due_to_rate_limit"], 1)
            self.assertIn("GIST_PUBLIC_RATE_LIMIT_EXHAUSTED", payload["limits_hit"])
            self.assertEqual(payload["anonymous_error_summary"], {"gist:HTTP_403": 1})
            self.assertEqual(payload["coverage_status"], "PARTIAL_API_ERRORS")
            self.assertFalse(any("/users/beta/gists" in url for url in calls))

    def test_forge_skips_metadata_proven_unusable_projects(self):
        from forge_source_discovery import gitlab_projects, codeberg_projects
        projects = [
            {"id": 1, "default_branch": "main", "empty_repo": True},
            {"id": 2, "default_branch": "main", "archived": True},
            {"id": 3, "default_branch": "main", "marked_for_deletion_on": "2026-11-02"},
            {"id": 4, "default_branch": "main", "repository_access_level": "disabled"},
            {"id": 5, "default_branch": "main"},
        ]
        self.assertEqual([x["id"] for x in gitlab_projects(projects)], [5])
        codeberg = {"data": [
            {"owner": {"login": "sample"}, "name": "empty", "default_branch": "main", "empty": True},
            {"owner": {"login": "sample"}, "name": "private", "default_branch": "main", "private": True},
            {"owner": {"login": "sample"}, "name": "ok", "default_branch": "main"},
        ]}
        self.assertEqual([x["name"] for x in codeberg_projects(codeberg)], ["ok"])

    def test_gitlab_keyset_pagination_never_reuses_numbered_page(self):
        calls = []
        def request(url):
            calls.append(url)
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if "/projects/42/repository/tree?" in url:
                # A full page without entry IDs cannot be continued
                # safely using keyset pagination.
                return [{"path": "dir_" + str(i), "type": "tree"} for i in range(100)]
            raise AssertionError(url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["errors"], [])
        self.assertIn("GITLAB_TREE_KEYSET_TOKEN_UNAVAILABLE", result["limits_hit"])
        self.assertEqual(result["coverage_status"], "PARTIAL_LIMITS")
        self.assertEqual(sum("/repository/tree?" in x for x in calls), 1)

    def test_gitlab_keyset_pagination_fetches_valid_next_page(self):
        calls = []
        def request(url):
            calls.append(url)
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if "/projects/42/repository/tree?" in url:
                if "page_token=last_key" in url:
                    return [{"path": "tr.m3u", "type": "blob", "id": "final_key"}]
                return [{"path": "folder/" + str(i), "type": "tree",
                         "id": "last_key" if i == 99 else str(i)} for i in range(100)]
            raise AssertionError(url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["coverage_status"], "COMPLETE_QUERIES")
        self.assertTrue(any("page_token=last_key" in url for url in calls))

if __name__ == "__main__":
    unittest.main()
