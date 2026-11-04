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


    def test_gitlab_stale_default_branch_recovery_only_when_project_is_publicly_verified(self):
        from urllib.error import HTTPError
        calls = []
        def request(url):
            calls.append(url)
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "old"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if "/projects/42/repository/tree?" in url:
                if "ref=old" in url:
                    raise HTTPError(url, 404, "stale branch", {}, None)
                self.assertIn("ref=main", url)
                return [{"type": "blob", "path": "tv.m3u"}]
            if url.endswith("/api/v4/projects/42"):
                return {"id": 42, "default_branch": "main", "empty_repo": False}
            raise AssertionError(url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["gitlab_stale_branch_recoveries"], 1)
        self.assertEqual(result["gitlab_confirmed_empty_projects_skipped"], 0)
        self.assertTrue(any(x.endswith("/api/v4/projects/42") for x in calls))

    def test_gitlab_confirmed_empty_repo_is_skipped_without_fabricated_sources(self):
        from urllib.error import HTTPError
        def request(url):
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if "/projects/42/repository/tree?" in url:
                raise HTTPError(url, 404, "empty", {}, None)
            if url.endswith("/api/v4/projects/42"):
                return {"id": 42, "default_branch": "main", "empty_repo": True}
            raise AssertionError(url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["source_count"], 0)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["gitlab_confirmed_empty_projects_skipped"], 1)
        self.assertFalse(result["playback_verified"])

    def test_gitlab_unverified_404_is_still_a_source_error(self):
        from urllib.error import HTTPError
        def request(url):
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if "/projects/42/repository/tree?" in url or url.endswith("/api/v4/projects/42"):
                raise HTTPError(url, 404, "not found", {}, None)
            raise AssertionError(url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["coverage_status"], "PARTIAL_API_ERRORS")
        self.assertEqual(result["anonymous_error_summary"], {"gitlab:HTTP_404": 1})
        self.assertEqual(result["gitlab_confirmed_empty_projects_skipped"], 0)


    def test_gitlab_public_path_recovers_reindexed_project(self):
        from urllib.error import HTTPError
        calls = []
        def request(url):
            calls.append(url)
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "old",
                         "path_with_namespace": "public-group/iptv-list"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if "/projects/42/repository/tree?" in url:
                raise HTTPError(url, 404, "stale index", {}, None)
            if url.endswith("/api/v4/projects/42"):
                raise HTTPError(url, 404, "old id missing", {}, None)
            if url.endswith("/api/v4/projects/public-group%2Fiptv-list"):
                return {"id": 99, "default_branch": "main",
                        "path_with_namespace": "public-group/iptv-list"}
            if "/projects/99/repository/tree?" in url:
                return [{"type": "blob", "path": "tr.m3u"}]
            raise AssertionError(url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["gitlab_relocated_projects_recovered"], 1)
        self.assertTrue(any("/projects/99/repository/files/tr.m3u/raw?" in x["source_url"]
                            for x in result["sources"]))
        self.assertFalse(result["playback_verified"])

    def test_gitlab_public_path_mismatch_remains_error(self):
        from urllib.error import HTTPError
        def request(url):
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main",
                         "path_with_namespace": "public-group/iptv-list"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if "/projects/42/repository/tree?" in url or url.endswith("/api/v4/projects/42"):
                raise HTTPError(url, 404, "gone", {}, None)
            if url.endswith("/api/v4/projects/public-group%2Fiptv-list"):
                return {"id": 99, "default_branch": "main",
                        "path_with_namespace": "different-owner/iptv-list"}
            raise AssertionError(url)
        result = forge.scan(request, terms=("iptv",))
        self.assertEqual(result["source_count"], 0)
        self.assertEqual(result["anonymous_error_summary"], {"gitlab:ValueError": 1})
        self.assertEqual(result["coverage_status"], "PARTIAL_API_ERRORS")


    def test_gitlab_404_recovers_only_verified_default_branch_without_ref(self):
        from urllib.error import HTTPError
        calls=[]
        def request(url):
            calls.append(url)
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch":"main",
                         "path_with_namespace":"official-iptv/channels"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data":[]}
            if url.endswith("/api/v4/projects/42"):
                return {"id":42, "default_branch":"main", "empty_repo":False}
            if "/projects/42/repository/tree?" in url:
                if "ref=main" in url:
                    raise HTTPError(url,404,"missing explicit ref",{},None)
                return [{"type":"blob", "path":"tr.m3u"}]
            raise AssertionError(url)
        report=forge.scan(request,terms=("iptv",))
        self.assertEqual(report["errors"],[])
        self.assertEqual(report["source_count"],1)
        self.assertEqual(report["gitlab_default_ref_tree_recoveries"],1)
        self.assertEqual(report["gitlab_stale_branch_recoveries"],0)
        self.assertEqual(report["coverage_status"],"COMPLETE_QUERIES")
        self.assertTrue(any("/repository/tree?" in x and "ref=" not in x
                            for x in calls))
        self.assertFalse(report["playback_verified"])

    def test_gitlab_both_ref_and_default_404_is_honestly_reported(self):
        from urllib.error import HTTPError
        def request(url):
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id":42, "default_branch":"main"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data":[]}
            if url.endswith("/api/v4/projects/42"):
                return {"id":42, "default_branch":"main", "empty_repo":False}
            if url.endswith("/projects/42/repository/branches?per_page=20"):
                # No verified alternative branch: source must stay 404.
                return []
            if "/projects/42/repository/tree?" in url:
                raise HTTPError(url,404,"not accessible",{},None)
            if url.endswith("/projects/42/repository/branches?per_page=20"):
                # Public project exists, but no verified default branch is
                # available. The 404 must remain an explicit error.
                return []
            raise AssertionError(url)
        report=forge.scan(request,terms=("iptv",))
        self.assertEqual(report["source_count"],0)
        self.assertEqual(report["anonymous_error_summary"],{"gitlab:HTTP_404":1})
        self.assertEqual(report["coverage_status"],"PARTIAL_API_ERRORS")


    def test_gitlab_public_default_branch_listing_recovers_stale_tree(self):
        from urllib.error import HTTPError
        called=[]
        def request(url):
            called.append(url)
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main",
                         "path_with_namespace": "public/tv"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if url.endswith("/api/v4/projects/42"):
                return {"id": 42, "default_branch": "main", "empty_repo": False}
            if url.endswith("/projects/42/repository/branches?per_page=20"):
                return [{"name": "real-tr-branch", "default": True},
                        {"name": "private-branch", "default": False}]
            if "/projects/42/repository/tree?" in url:
                if "ref=real-tr-branch" in url:
                    return [{"type": "blob", "path": "tr.m3u8"}]
                raise HTTPError(url, 404, "Stale default", {}, None)
            raise AssertionError(url)
        report = forge.scan(request, terms=("iptv",))
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["source_count"], 1)
        self.assertEqual(report["gitlab_public_branch_listing_recoveries"], 1)
        self.assertIn("ref=real-tr-branch", report["sources"][0]["source_url"])
        self.assertFalse(report["playback_verified"])

    def test_gitlab_unverified_branch_404_is_not_hidden(self):
        from urllib.error import HTTPError
        def request(url):
            if "gitlab.com/api/v4/projects?" in url:
                return [{"id": 42, "default_branch": "main"}]
            if "codeberg.org/api/v1/repos/search?" in url:
                return {"data": []}
            if url.endswith("/api/v4/projects/42"):
                return {"id": 42, "default_branch": "main", "empty_repo": False}
            if "/projects/42/repository/branches?" in url:
                return [{"name": "some-other", "default": False}]
            if "/projects/42/repository/tree?" in url:
                raise HTTPError(url, 404, "Not available", {}, None)
            raise AssertionError(url)
        report = forge.scan(request, terms=("iptv",))
        self.assertEqual(report["source_count"], 0)
        self.assertEqual(report["anonymous_error_summary"], {"gitlab:HTTP_404": 1})
        self.assertEqual(report["gitlab_public_branch_listing_recoveries"], 0)

if __name__ == "__main__":
    unittest.main()
