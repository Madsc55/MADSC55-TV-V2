import unittest
import urllib.request
from discovery_34 import QUERIES, SOURCES, identity, search_url, repository_candidates, curated_candidates

class Discovery34Tests(unittest.TestCase):
    def test_sources(self):
        self.assertEqual(len(SOURCES), 6)
        self.assertIn("tr.m3u8", QUERIES)
    def test_search(self):
        for source in ("github", "gitlab", "codeberg"):
            self.assertIn("turkiye.m3u", __import__("urllib.parse", fromlist=["unquote"]).unquote(search_url(source, "turkiye.m3u")))
    def test_repositories(self):
        cases = [("github", {"items": [{"html_url": "https://github.com/a/b"}]}),
                 ("gitlab", [{"web_url": "https://gitlab.com/a/b"}]),
                 ("codeberg", {"data": [{"html_url": "https://codeberg.org/a/b"}]})]
        for source, payload in cases:
            self.assertFalse(repository_candidates(source, payload)[0]["verified_av"])
    def test_repository_api_error_objects_fail_closed(self):
        cases = (("github", {"message": "API rate limit exceeded"}),
                 ("github", {}),
                 ("gitlab", {"message": "Too Many Requests"}),
                 ("codeberg", {"message": "rate limit"}),
                 ("codeberg", {"ok": False, "data": []}),
                 ("codeberg", {}))
        for source, payload in cases:
            with self.subTest(source=source, payload=payload), self.assertRaises(ValueError):
                repository_candidates(source, payload)
        self.assertEqual(repository_candidates("github", {"items": []}), [])
        self.assertEqual(repository_candidates("gitlab", []), [])
        self.assertEqual(repository_candidates("codeberg", {"data": []}), [])

    def test_candidate_fetch_retries_transient_http_then_succeeds(self):
        import io
        import urllib.error
        from discovery_34 import fetch_with_retry
        attempts, waits = [], []
        def fetch(url):
            attempts.append(url)
            if len(attempts) < 3:
                raise urllib.error.HTTPError(url, 503, "Unavailable", {}, io.BytesIO())
            return {"items": []}
        self.assertEqual(fetch_with_retry("https://api.github.com/search/repositories",
                                          fetch=fetch, sleep=waits.append), {"items": []})
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(waits), 2)

    def test_candidate_fetch_does_not_retry_nontransient_http(self):
        import io
        import urllib.error
        from discovery_34 import fetch_with_retry
        attempts = []
        def fetch(url):
            attempts.append(url)
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, io.BytesIO())
        with self.assertRaises(urllib.error.HTTPError):
            fetch_with_retry("https://api.github.com/search/repositories",
                             fetch=fetch, sleep=lambda seconds: self.fail("unexpected sleep"))
        self.assertEqual(len(attempts), 1)

    def test_network_cli_stops_codeberg_fanout_after_429(self):
        import io
        import json
        import tempfile
        import urllib.error
        from unittest.mock import patch
        from pathlib import Path
        import discovery_34
        calls = []
        def fake_fetch(url):
            calls.append(url)
            if "codeberg.org" in url:
                raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, io.BytesIO())
            return [] if "gitlab.com" in url else {"items": []}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidates.json"
            with patch.object(discovery_34, "fetch_json", side_effect=fake_fetch), \
                 patch.object(discovery_34.time, "sleep", return_value=None), \
                 patch("prescan_readiness_gate.inspect", return_value={"ready": True}), \
                 patch("sys.argv", ["discovery_34.py", "--network", "--output", str(output)]):
                with self.assertRaises(SystemExit) as exit_result:
                    discovery_34.main()
                self.assertEqual(exit_result.exception.code, 1)
            report = json.loads(output.read_text())
        self.assertEqual(sum("codeberg.org" in url for url in calls), 3)
        self.assertEqual(len(report["errors"]), len(QUERIES))
        self.assertEqual(sum(row["error"] == "provider_rate_limit_skipped" for row in report["errors"]), len(QUERIES) - 1)
        self.assertEqual(report["av_verified"], 0)

    def test_network_cli_stops_github_fanout_after_rate_limited_403(self):
        import io
        import json
        import tempfile
        import urllib.error
        from pathlib import Path
        from unittest.mock import patch
        import discovery_34
        calls = []
        def fake_fetch(url):
            calls.append(url)
            if "api.github.com" in url:
                raise urllib.error.HTTPError(
                    url, 403, "API rate limit exceeded",
                    {"X-RateLimit-Remaining": "0"}, io.BytesIO())
            if "gitlab.com" in url:
                return []
            return {"data": []}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidates.json"
            with patch.object(discovery_34, "fetch_json", side_effect=fake_fetch), \
                 patch("prescan_readiness_gate.inspect", return_value={"ready": True}), \
                 patch("sys.argv", ["discovery_34.py", "--network", "--output", str(output)]):
                with self.assertRaises(SystemExit) as exit_result:
                    discovery_34.main()
                self.assertEqual(exit_result.exception.code, 1)
            report = json.loads(output.read_text())
        self.assertEqual(sum("api.github.com" in url for url in calls), 1)
        self.assertEqual(len(report["errors"]), len(QUERIES))
        self.assertEqual(sum(row["error"] == "provider_rate_limit_skipped" for row in report["errors"]), len(QUERIES) - 1)
        self.assertEqual(report["av_verified"], 0)

    def test_network_cli_http_200_throttle_stops_real_provider_queries(self):
        import json
        import tempfile
        import time
        from pathlib import Path
        from unittest.mock import patch
        import discovery_34
        cases = [
            ("github", {"message": "secondary rate limit", "items": []}),
            ("codeberg", {"error": "too many requests", "data": []}),
            ("gitlab", {"message": "Rate limit exceeded"}),
        ]
        for provider, envelope in cases:
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as directory:
                calls = []
                def fake_fetch(url):
                    calls.append(url)
                    if provider == "github" and "api.github.com" in url:
                        return envelope
                    if provider == "gitlab" and "gitlab.com" in url:
                        return envelope
                    if provider == "codeberg" and "codeberg.org" in url:
                        return envelope
                    return ({"items": []} if "api.github.com" in url else
                            [] if "gitlab.com" in url else {"data": []})
                output = Path(directory) / "candidates.json"
                with patch.object(discovery_34, "fetch_json", side_effect=fake_fetch), \
                     patch("prescan_readiness_gate.inspect", return_value={"ready": True}), \
                     patch("sys.argv", ["discovery_34.py", "--network", "--output", str(output)]):
                    with self.assertRaises(SystemExit) as result:
                        discovery_34.main()
                    self.assertEqual(result.exception.code, 1)
                report = json.loads(output.read_text())
                self.assertEqual(sum(
                    (("api.github.com" in url) if provider == "github" else
                     (provider + (".org" if provider == "codeberg" else ".com")) in url)
                    for url in calls), 1)
                rows = [row for row in report["errors"] if row["source"] == provider]
                self.assertEqual(len(rows), len(discovery_34.QUERIES))
                self.assertEqual(rows[0]["error"], "provider_throttled_response")
                self.assertGreater(rows[0]["retry_not_before"], int(time.time()))
                self.assertEqual(
                    sum(row["error"] == "provider_rate_limit_skipped" for row in rows),
                    len(discovery_34.QUERIES) - 1)
                self.assertNotIn("secondary rate limit", json.dumps(report))
                self.assertNotIn("too many requests", json.dumps(report))
                self.assertEqual(report["av_verified"], 0)

    def test_network_cli_secondary_403_abuse_throttle_opens_circuit(self):
        import io
        import json
        import tempfile
        import urllib.error
        from pathlib import Path
        from unittest.mock import patch
        import discovery_34
        calls = []
        def fake_fetch(url):
            calls.append(url)
            if "api.github.com" in url:
                raise urllib.error.HTTPError(
                    url, 403, "Forbidden", {},
                    io.BytesIO(b'{"message":"You have exceeded a secondary rate limit."}'))
            return [] if "gitlab.com" in url else {"data": []}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidates.json"
            with patch.object(discovery_34, "fetch_json", side_effect=fake_fetch), \
                 patch("prescan_readiness_gate.inspect", return_value={"ready": True}), \
                 patch("sys.argv", ["discovery_34.py", "--network", "--output", str(output)]):
                with self.assertRaises(SystemExit) as result:
                    discovery_34.main()
                self.assertEqual(result.exception.code, 1)
            report = json.loads(output.read_text())
        self.assertEqual(sum("api.github.com" in url for url in calls), 1)
        self.assertEqual(sum(row["error"] == "provider_rate_limit_skipped" for row in report["errors"]), len(QUERIES) - 1)
        self.assertEqual(report["av_verified"], 0)

    def test_resume_rejects_unknown_failure_queries_and_duplicate_completions(self):
        import json
        import tempfile
        from pathlib import Path
        from discovery_34 import QUERIES, REPOSITORY_SOURCES, load_resume
        plan = {source: list(QUERIES) for source in REPOSITORY_SOURCES}
        base = {"mode": "network", "av_verified": 0, "candidates": [],
                "errors": [], "query_plan": plan,
                "completed_queries": {source: [] for source in plan}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.json"
            bad_query = json.loads(json.dumps(base))
            bad_query["errors"] = [{"source": "github", "query": "not-in-plan", "error": "HTTPError"}]
            path.write_text(json.dumps(bad_query))
            with self.assertRaisesRegex(ValueError, "outside discovery plan"):
                load_resume(path, plan)
            duplicates = json.loads(json.dumps(base))
            duplicates["completed_queries"]["github"] = [QUERIES[0], QUERIES[0]]
            path.write_text(json.dumps(duplicates))
            with self.assertRaisesRegex(ValueError, "Invalid completed-query"):
                load_resume(path, plan)

    def test_resume_rejects_duplicate_source_identities(self):
        import json
        import tempfile
        from pathlib import Path
        from discovery_34 import QUERIES, REPOSITORY_SOURCES, load_resume, identity
        plan = {source: list(QUERIES) for source in REPOSITORY_SOURCES}
        candidate = identity("github", "https://github.com/example/playlist")
        report = {"mode": "network", "av_verified": 0,
                  "candidates": [candidate, dict(candidate)], "errors": [],
                  "query_plan": plan,
                  "completed_queries": {source: [] for source in plan}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.json"
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "Duplicate candidate identity"):
                load_resume(path, plan)

    def test_resume_rejects_query_plan_drift(self):
        import json
        import tempfile
        from pathlib import Path
        from discovery_34 import QUERIES, REPOSITORY_SOURCES, load_resume
        plan = {source: list(QUERIES) for source in REPOSITORY_SOURCES}
        stale_plan = {source: list(queries) for source, queries in plan.items()}
        stale_plan["github"] = stale_plan["github"][:-1]
        report = {"mode": "network", "av_verified": 0, "candidates": [],
                  "errors": [], "query_plan": stale_plan,
                  "completed_queries": {source: [] for source in stale_plan}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "previous.json"
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "query plan differs"):
                load_resume(path, plan)

    def test_youtube(self):
        items = curated_candidates("youtube", [{"video_id": "AbCdEf12345"}])
        self.assertEqual(items[0]["source_id"], "youtube:AbCdEf12345")
    def test_invalid(self):
        for url in ("file:///tmp/a", "https://localhost/a", "https://user:pass@site.org/a", "http://127.0.0.1/a", "http://192.168.1.1/a", "http://[::1]/a"):
            with self.assertRaises(ValueError):
                identity("m3u", url)
    def test_provider_host_boundaries(self):
        for source, url in (("github", "https://github.com.evil.example/a"),
                            ("gitlab", "http://gitlab.com/a"),
                            ("codeberg", "https://example.org/a"),
                            ("youtube", "https://youtu.be/AbCdEf12345")):
            with self.assertRaises(ValueError):
                identity(source, url)
    def test_provider_identity_rejects_port_and_fragment_bypass(self):
        for source, host in (("github", "github.com"), ("gitlab", "gitlab.com"),
                             ("codeberg", "codeberg.org"), ("youtube", "www.youtube.com")):
            for url in (f"https://{host}:8443/example", f"https://{host}/example#hidden"):
                with self.subTest(source=source, url=url), self.assertRaises(ValueError):
                    identity(source, url)
        self.assertEqual(identity("codeberg", "https://codeberg.org:443/example")["source"], "codeberg")

    def test_api_redirect_is_refused_before_followup_request(self):
        from discovery_34 import _NoRedirect
        handler = _NoRedirect()
        request = urllib.request.Request("https://api.github.com/search/repositories?q=test")
        with self.assertRaisesRegex(ValueError, "Redirect refused"):
            handler.redirect_request(request, None, 302, "Found", {}, "https://example.org/redirect")

    def test_malformed_external_candidate_urls_are_skipped(self):
        for source, payload in (("github", {"items": [{"html_url": None}, {"html_url": 123}, {"html_url": "https://github.com/a/b"}]}), ("gitlab", [{"web_url": []}, {"web_url": "https://gitlab.com/a/b"}]), ("codeberg", {"data": [{"html_url": {}}, {"html_url": "https://codeberg.org/a/b"}]})):
            self.assertEqual(len(repository_candidates(source, payload)), 1)
        for source in ("official", "m3u"):
            self.assertEqual(len(curated_candidates(source, [{"url": None}, {"url": 123}, {"url": "https://example.org/live.m3u8"}])), 1)

    def test_malformed_curated_records_are_skipped(self):
        for source in ("official", "m3u", "youtube"):
            records = [None, 7, [], "not-a-record"]
            records.append({"video_id": "AbCdEf12345"} if source == "youtube" else {"url": "https://example.org/live.m3u8"})
            self.assertEqual(len(curated_candidates(source, records)), 1)

    def test_youtube_invalid_video_id_types(self):
        records = [{"video_id": None}, {"video_id": 123}, {"video_id": []}, {"video_id": {}}, {"video_id": "AbCdEf12345"}]
        self.assertEqual(len(curated_candidates("youtube", records)), 1)

    def test_control_characters_and_invalid_url_types_rejected(self):
        for source in ("official", "m3u"):
            for url in ("https://example.org/a.m3u8\n#EXTINF", "https://example.org/a\rnext", "https://example.org/a\x00", "https://example.org/a\x7f", None, 123):
                with self.subTest(source=source, url=url), self.assertRaises(ValueError):
                    identity(source, url)
            self.assertEqual(curated_candidates(source, [{"url": "https://example.org/a\n#EXTINF"}]), [])

    def test_signed_and_port_specific_stream_urls_keep_unique_safe_ids(self):
        for source in ("official", "m3u"):
            a = identity(source, "https://example.org/live.m3u8?token=SECRET_A")
            b = identity(source, "https://example.org/live.m3u8?token=SECRET_B")
            self.assertNotEqual(a["source_id"], b["source_id"])
            self.assertNotIn("SECRET_A", a["source_id"])
            self.assertNotIn("SECRET_B", b["source_id"])
            self.assertFalse(a["verified_av"])
        standard = identity("m3u", "https://example.org/live.m3u8")
        alternate = identity("m3u", "https://example.org:8443/live.m3u8")
        self.assertNotEqual(standard["source_id"], alternate["source_id"])
        self.assertIn(":8443", alternate["source_id"])

    def test_malformed_port_fail_closed_without_dropping_valid_candidates(self):
        for url in ("https://example.org:99999/live.m3u8", "https://example.org:bad/live.m3u8"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "Invalid URL port"):
                identity("m3u", url)
        records = [{"url": "https://example.org:99999/live.m3u8"},
                   {"url": "https://example.org/live.m3u8?token=VALID"}]
        result = curated_candidates("m3u", records)
        self.assertEqual(len(result), 1)
        self.assertNotIn("VALID", result[0]["source_id"])

    def test_discovery_cli_preserves_existing_report_bytes(self):
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "protected-discovery.json"
            original = b"DO_NOT_OVERWRITE_DISCOVERY_REPORT"
            output.write_bytes(original)
            script = Path(__file__).with_name("discovery_34.py")
            result = subprocess.run(
                [sys.executable, str(script), "--output", str(output)],
                capture_output=True, text=True, timeout=30
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), original)

    def test_resume_preserves_candidates_and_only_retries_incomplete_queries(self):
        import json
        import sys
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import discovery_34

        def first_fetch(url):
            if "github.com" in url:
                return {"items": [{"html_url": "https://github.com/example/channels"}],
                        "incomplete_results": "turkiye.m3u" in url}
            return [] if "gitlab.com" in url else {"data": []}

        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original.json"
            output = Path(directory) / "resumed.json"
            options = ["discovery_34.py", "--network"]
            with patch("prescan_readiness_gate.inspect", return_value={"ready": True}):
                with (patch.object(sys, "argv", options + ["--output", str(original)]),
                      patch.object(discovery_34, "fetch_with_retry", side_effect=first_fetch)):
                    with self.assertRaises(SystemExit) as failed:
                        discovery_34.main()
                    self.assertEqual(failed.exception.code, 1)
                original_data = original.read_bytes()
                self.assertEqual(len(json.loads(original_data)["candidates"]), 1)
                with (patch.object(sys, "argv", options + ["--resume", str(original), "--output", str(output)]),
                      patch.object(discovery_34, "fetch_with_retry", return_value={"items": []}) as fetch):
                    discovery_34.main()
                    fetch.assert_called_once_with(search_url("github", "turkiye.m3u"))
                report = json.loads(output.read_text())
                self.assertEqual(original.read_bytes(), original_data)
        self.assertEqual(report["queries_reused"], 17)
        self.assertEqual(report["queries_attempted_this_run"], 1)
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["av_verified"], 0)

    def test_resume_honors_provider_wait_recorded_in_previous_report(self):
        import json
        import sys
        import tempfile
        import urllib.error
        from pathlib import Path
        from unittest.mock import patch
        import discovery_34

        def first_fetch(url):
            if "codeberg.org" in url:
                raise urllib.error.HTTPError(url, 429, "Too Many Requests", {"Retry-After": "600"}, None)
            return [] if "gitlab.com" in url else {"items": []}

        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original.json"
            output = Path(directory) / "resumed.json"
            options = ["discovery_34.py", "--network"]
            with (patch("prescan_readiness_gate.inspect", return_value={"ready": True}),
                  patch.object(discovery_34.time, "time", return_value=1000)):
                with (patch.object(sys, "argv", options + ["--output", str(original)]),
                      patch.object(discovery_34, "fetch_with_retry", side_effect=first_fetch)):
                    with self.assertRaises(SystemExit):
                        discovery_34.main()
                with (patch.object(sys, "argv", options + ["--resume", str(original), "--output", str(output)]),
                      patch.object(discovery_34, "fetch_with_retry") as fetch):
                    with self.assertRaises(SystemExit) as failed:
                        discovery_34.main()
                    self.assertEqual(failed.exception.code, 1)
                    fetch.assert_not_called()
                report = json.loads(output.read_text())
        self.assertEqual(report["queries_reused"], 12)
        self.assertEqual(report["queries_attempted_this_run"], 0)
        self.assertEqual(len(report["errors"]), 6)
        self.assertTrue(all(row["retry_not_before"] == 1600 for row in report["errors"]))

    def test_official_and_m3u(self):
        for source in ("official", "m3u"):
            self.assertEqual(len(curated_candidates(source, [{"url": "https://example.org/live.m3u8"}])), 1)

    def test_ambiguous_backslash_urls_rejected(self):
        for source, url in (("github", "https://github.com\\@evil.example/a"),
                            ("m3u", "https://example.org\\@127.0.0.1/live.m3u8"),
                            ("official", "https://example.org/live\\segment.m3u8")):
            with self.subTest(source=source), self.assertRaises(ValueError):
                identity(source, url)

if __name__ == "__main__":
    unittest.main()
