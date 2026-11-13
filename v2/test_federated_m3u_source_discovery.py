import unittest
import urllib.error
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

if __name__ == "__main__":
    unittest.main()
