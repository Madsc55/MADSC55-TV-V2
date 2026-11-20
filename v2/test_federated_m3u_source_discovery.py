import unittest
import urllib.error
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import federated_m3u_source_discovery as discovery
from federated_m3u_source_discovery import FEDERATED_QUERIES, discover_provider

PLAYLIST = "#EXTM3U\n#EXTINF:-1,TRT Haber\nhttps://cdn.example/live.m3u8\n"

class FederatedM3UDiscoveryTests(unittest.TestCase):
    def test_federated_queries_include_generic_playlist_terms(self):
        for term in ("turkiye.m3u", "tr.m3u8", "turkish-iptv", "iptv",
                     "m3u", "m3u8", "playlist", "live tv", "television"):
            self.assertIn(term, FEDERATED_QUERIES)
        self.assertEqual(len(FEDERATED_QUERIES), len(set(FEDERATED_QUERIES)))
    def test_http_200_provider_error_objects_fail_closed(self):
        cases = (("gitlab", {"message": "rate limit exceeded"}),
                 ("gitlab", None),
                 ("codeberg", {"message": "rate limit exceeded"}),
                 ("codeberg", {"ok": False, "data": []}),
                 ("codeberg", {"data": {"message": "error"}}),
                 ("codeberg", []))
        for provider, payload in cases:
            with self.subTest(provider=provider, payload=payload):
                result = discover_provider(
                    provider,
                    fetch_json_fn=lambda _url, p=payload: p,
                    fetch_text_fn=lambda *_: self.fail("invalid search must not fetch files"),
                    sleep_fn=lambda _: self.fail("invalid response must not retry"),
                    queries=("iptv",))
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["queries_checked"], 1)
                self.assertEqual(result["queries_failed"], 1)
                self.assertEqual(result["projects_discovered"], 0)
                self.assertEqual(result["sources_found"], 0)
                self.assertEqual(result["query_results"][0]["reason"], "InvalidResponse")

    def test_malformed_branch_metadata_is_not_discovered(self):
        for provider, payload in (
            ("gitlab", [{"id": 123, "path_with_namespace": "team/tv", "default_branch": ["bad"]}]),
            ("codeberg", {"data": [{"full_name": "team/tv", "default_branch": ["bad"]}]}),
        ):
            with self.subTest(provider=provider):
                result = discover_provider(provider, fetch_json_fn=lambda _: payload,
                                           fetch_text_fn=lambda *_: self.fail("must not fetch"),
                                           queries=("iptv",))
                self.assertEqual(result["projects_discovered"], 0)
                self.assertEqual(result["sources_found"], 0)

    def test_invalid_raw_playlist_is_reported_without_crash(self):
        def api(url):
            if "/repository/tree?" in url:
                return [{"type": "blob", "path": "channels.m3u"}]
            return [{"id": 123, "path_with_namespace": "team/tv", "default_branch": "main"}]
        result = discover_provider("gitlab", fetch_json_fn=api,
                                   fetch_text_fn=lambda *_: (_ for _ in ()).throw(ValueError("bad encoding")),
                                   queries=("iptv",))
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["sources_found"], 0)
        self.assertEqual(result["errors"][0]["error"], "ValueError")

    def test_gitlab_project_tree_and_raw_m3u_are_discovered(self):
        calls, fetched = [], []
        def api(url):
            calls.append(url)
            if "/api/v4/projects?" in url:
                return [{"id": 123, "path_with_namespace": "team/tv-list", "default_branch": "main"}]
            if "/repository/tree?" in url:
                return [{"type": "blob", "path": "playlists/tr.m3u"}]
            raise AssertionError(url)
        def raw(url, host):
            fetched.append((url, host))
            return PLAYLIST
        result = discover_provider("gitlab", fetch_json_fn=api, fetch_text_fn=raw,
                                   queries=("turkiye.m3u", "tr.m3u8"))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["projects_discovered"], 1)
        self.assertEqual(result["sources_found"], 1)
        self.assertEqual(result["sources"][0]["repository"], "team/tv-list")
        self.assertEqual(result["sources"][0]["entries"], 1)
        self.assertEqual(fetched[0][1], "gitlab.com")
        self.assertEqual(result["queries_checked"], 2)

    def test_http_200_repository_tree_error_objects_fail_closed(self):
        for provider, bad_tree in (("gitlab", {"message": "rate limited"}),
                                   ("gitlab", None),
                                   ("codeberg", {"message": "blocked"}),
                                   ("codeberg", {"tree": {"message": "rate limited"}})):
            with self.subTest(provider=provider, bad_tree=bad_tree):
                def api(url):
                    if "/repository/tree?" in url or "/git/trees/" in url:
                        return bad_tree
                    if provider == "gitlab":
                        return [{"id": 123, "path_with_namespace": "team/tv-list",
                                 "default_branch": "main"}]
                    return {"data": [{"full_name": "team/tv-list",
                                      "default_branch": "main"}]}
                result = discover_provider(
                    provider, fetch_json_fn=api,
                    fetch_text_fn=lambda *_: self.fail("invalid tree must not read raw files"),
                    sleep_fn=lambda _: self.fail("invalid 200 must not retry"),
                    queries=("iptv",))
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["sources_found"], 0)
                self.assertEqual(result["errors"][0]["error"], "InvalidTreeResponse")

    def test_codeberg_repo_tree_and_raw_m3u_are_discovered(self):
        calls, fetched = [], []
        def api(url):
            calls.append(url)
            if "/api/v1/repos/search?" in url:
                return {"data": [{"full_name": "team/tv-list", "default_branch": "main"}]}
            if "/git/trees/" in url:
                return {"tree": [{"type": "blob", "path": "tr.m3u8"}]}
            raise AssertionError(url)
        def raw(url, host):
            fetched.append((url, host))
            return PLAYLIST
        result = discover_provider("codeberg", fetch_json_fn=api, fetch_text_fn=raw,
                                   queries=("turkiye.m3u",))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["projects_discovered"], 1)
        self.assertEqual(result["sources_found"], 1)
        self.assertEqual(result["sources"][0]["repository"], "team/tv-list")
        self.assertEqual(fetched[0][1], "codeberg.org")
        self.assertEqual(result["queries_checked"], 1)

    def test_provider_429_retries_then_skips_remaining_terms(self):
        calls, sleeps = [], []
        def api(url):
            calls.append(url)
            raise urllib.error.HTTPError(url, 429, "rate limited", {}, None)
        result = discover_provider("codeberg", fetch_json_fn=api,
                                   fetch_text_fn=lambda *_: self.fail("must not fetch"),
                                   sleep_fn=sleeps.append,
                                   queries=("turkiye.m3u", "tr.m3u8", "turkish-iptv"))
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["rate_limited"])
        self.assertEqual(result["queries_total"], 3)
        self.assertEqual(result["queries_checked"], 1)
        self.assertEqual(result["queries_skipped"], 2)
        self.assertEqual(result["queries_failed"], 1)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [30, 60])
        self.assertEqual([x["status"] for x in result["query_results"]],
                         ["error", "skipped", "skipped"])

    def test_github_style_403_rate_limit_opens_provider_circuit(self):
        calls = []
        def api(url):
            calls.append(url)
            raise urllib.error.HTTPError(url, 403, "rate limit exceeded",
                                         {"X-RateLimit-Remaining": "0"}, None)
        result = discover_provider("gitlab", fetch_json_fn=api,
                                   fetch_text_fn=lambda *_: self.fail("must not fetch"),
                                   sleep_fn=lambda _: self.fail("403 must not retry"),
                                   queries=("turkiye.m3u", "tr.m3u8"))
        self.assertTrue(result["rate_limited"])
        self.assertEqual(result["queries_checked"], 1)
        self.assertEqual(result["queries_skipped"], 1)
        self.assertEqual(len(calls), 1)

    def test_circuit_does_not_read_a_project_discovered_before_throttling(self):
        calls = []
        def api(url):
            calls.append(url)
            if len(calls) == 1:
                return {"ok": True, "data": [{"full_name": "team/channels"}]}
            if len(calls) == 2:
                raise urllib.error.HTTPError(url, 429, "Throttled", {"Retry-After": "600"}, None)
            self.fail("throttled provider must not receive tree or search requests")
        result = discover_provider("codeberg", fetch_json_fn=api,
                                   fetch_text_fn=lambda *_: self.fail("must not read raw files"),
                                   sleep_fn=lambda _: self.fail("must not retry before Retry-After"),
                                   queries=("first", "second", "third"))
        self.assertEqual(result["projects_discovered"], 1)
        self.assertEqual(result["queries_skipped"], 1)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["rate_limited"])

    def test_transient_tree_and_raw_failures_recover_in_budget(self):
        tree_calls, raw_calls, sleeps = [], [], []
        def api(url):
            if "/api/v1/repos/search?" in url:
                return {"ok": True, "data": [{"full_name": "team/channels"}]}
            tree_calls.append(url)
            if len(tree_calls) == 1:
                raise urllib.error.URLError("temporary connection failure")
            return {"tree": [{"type": "blob", "path": "tr.m3u8"}]}
        def raw(url, _host):
            raw_calls.append(url)
            if len(raw_calls) == 1:
                raise urllib.error.HTTPError(url, 503, "Unavailable", {}, None)
            return PLAYLIST
        result = discover_provider("codeberg", fetch_json_fn=api, fetch_text_fn=raw,
                                   sleep_fn=sleeps.append, queries=("first",))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sources_found"], 1)
        self.assertEqual(len(tree_calls), 2)
        self.assertEqual(len(raw_calls), 2)
        self.assertEqual(sleeps, [1, 1])

    def test_cli_persists_both_reports_and_fails_on_partial_discovery(self):
        reports = [
            {"status": "ok", "projects_discovered": 0, "sources_found": 0, "sources": []},
            {"status": "error", "projects_discovered": 0, "sources_found": 0, "sources": []},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (patch.object(discovery, "ROOT", root),
                  patch.object(discovery, "discover_provider", side_effect=reports) as discover):
                with self.assertRaises(SystemExit) as failed:
                    discovery.main()
                self.assertEqual(failed.exception.code, 1)
                with self.assertRaisesRegex(SystemExit, "already exists"):
                    discovery.main()
                self.assertEqual(discover.call_count, 2)
            for provider, expected in zip(("gitlab", "codeberg"), reports):
                path = root / "v2/reports" / f"{provider}-m3u-source-discovery.json"
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], expected["status"])

if __name__ == "__main__":
    unittest.main()
