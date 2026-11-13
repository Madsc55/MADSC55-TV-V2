#!/usr/bin/env python3
"""Offline regression for bounded #34 live metadata retries."""
import unittest
import urllib.error
from discovery_34_live_contract import probe, probe_queries

def http_error(code):
    return urllib.error.HTTPError("https://codeberg.org/api/v1/repos/search", code, "test", {}, None)

class LiveContractRetryTests(unittest.TestCase):
    def test_transient_recovery(self):
        calls = []
        sleeps = []
        def fetch(_url):
            calls.append(1)
            if len(calls) < 3:
                raise http_error(503)
            return {"data": [{"html_url": "https://codeberg.org/a/b"}]}
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["candidates"], 1)
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(sleeps, [1, 2])

    def test_http_200_error_objects_fail_closed(self):
        for source, payload in (("github", {"message": "rate limited"}),
                                ("gitlab", {"message": "forbidden"}),
                                ("codeberg", {"message": "error"})):
            with self.subTest(source=source):
                result = probe(source, fetch=lambda _, p=payload: p,
                               sleep=lambda _: self.fail("unexpected retry"))
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["reason"], "ValueError")
                self.assertEqual(result["attempts"], 1)

    def test_empty_valid_repository_lists_are_allowed(self):
        for source, payload in (("github", {"items": []}),
                                ("gitlab", []), ("codeberg", {"data": []})):
            with self.subTest(source=source):
                result = probe(source, fetch=lambda _, p=payload: p,
                               sleep=lambda _: self.fail("unexpected retry"))
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["candidates"], 0)

    def test_non_retryable_failure(self):
        calls = []
        def fetch(_url):
            calls.append(1)
            raise http_error(403)
        result = probe("codeberg", fetch=fetch, sleep=lambda _: self.fail("unexpected sleep"))
        self.assertEqual(result["reason"], "HTTP_403")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(len(calls), 1)

    def test_connection_error_recovers(self):
        attempts = []
        sleeps = []
        def fetch(_url):
            attempts.append(1)
            if len(attempts) == 1:
                raise urllib.error.URLError("temporary network failure")
            return {"data": []}
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(sleeps, [1])

    def test_connection_error_exhaustion_fails_closed(self):
        result = probe("codeberg", fetch=lambda _: (_ for _ in ()).throw(urllib.error.URLError("offline")), sleep=lambda _: None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "URLError")
        self.assertEqual(result["attempts"], 3)

    def test_codeberg_404_fails_without_retry(self):
        calls = []
        def fetch(_url):
            calls.append(1)
            raise http_error(404)
        result = probe("codeberg", fetch=fetch, sleep=lambda _: self.fail("unexpected retry"))
        self.assertEqual(result["reason"], "HTTP_404")
        self.assertFalse(result["retryable"])
        self.assertEqual(result["provider"], "codeberg")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(len(calls), 1)

    def test_http_408_recovers_within_retry_budget(self):
        calls, sleeps = [], []
        def fetch(_url):
            calls.append(1)
            if len(calls) == 1:
                raise http_error(408)
            return {"data": []}
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(sleeps, [1])

    def test_codeberg_500_exhausts_retry_budget(self):
        calls, sleeps = [], []
        def fetch(_url):
            calls.append(1)
            raise http_error(500)
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["reason"], "HTTP_500")
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [1, 2])

    def test_timeout_recovers(self):
        calls, sleeps = [], []
        def fetch(_url):
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError("timed out")
            return {"data": []}
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(sleeps, [1])

    def test_connection_reset_exhaustion_fails_closed(self):
        result = probe("codeberg",
                       fetch=lambda _: (_ for _ in ()).throw(ConnectionResetError("reset")),
                       sleep=lambda _: None)
        self.assertEqual(result["reason"], "ConnectionResetError")
        self.assertEqual(result["attempts"], 3)
        self.assertTrue(result["retryable"])

    def test_exhaustion_fails_closed(self):
        result = probe("codeberg", fetch=lambda _: (_ for _ in ()).throw(http_error(429)), sleep=lambda _: None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["attempts"], 3)
        self.assertTrue(result["retryable"])

    def test_http_408_retry(self):
        calls = []
        def fetch(_url):
            calls.append(1)
            if len(calls) == 1:
                raise http_error(408)
            return {"data": []}
        result = probe("codeberg", fetch=fetch, sleep=lambda _: None)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attempts"], 2)

    def test_error_endpoint_host(self):
        result = probe("codeberg", fetch=lambda _: (_ for _ in ()).throw(http_error(403)), sleep=lambda _: None)
        self.assertEqual(result["reason"], "HTTP_403")
        self.assertEqual(result["endpoint_host"], "codeberg.org")

    def test_all_discovery_queries_are_checked(self):
        from urllib.parse import urlsplit, parse_qs
        seen = []
        def fetch(url):
            query = parse_qs(urlsplit(url).query).get("q", [""])[0]
            seen.append(query)
            return {"items": []}
        terms = ("turkiye.m3u", "tr.m3u8", "turkish-iptv")
        result = probe_queries("github", queries=terms, fetch=fetch,
                               sleep=lambda _: self.fail("unexpected retry"))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["queries_checked"], 3)
        self.assertEqual(result["queries_ok"], 3)
        self.assertEqual(seen, list(terms))

    def test_query_matrix_preserves_provider_failures(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if "tr.m3u8" in url:
                raise http_error(403)
            return {"data": []}
        result = probe_queries("codeberg", queries=("turkiye.m3u", "tr.m3u8", "canli-tv"),
                               fetch=fetch, sleep=lambda _: self.fail("403 must not retry"))
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["queries_checked"], 3)
        self.assertEqual(result["queries_failed"], 1)
        self.assertEqual(result["query_results"][1]["http_status"], 403)
        self.assertEqual(result["query_results"][1]["endpoint_host"], "codeberg.org")
        self.assertEqual(len(calls), 3)

    def test_http_error_exposes_safe_rate_limit_diagnostics(self):
        exc = urllib.error.HTTPError("https://codeberg.org/api/v1/repos/search", 403,
                                     "Forbidden", {"X-RateLimit-Remaining": "0"}, None)
        result = probe("codeberg", fetch=lambda _: (_ for _ in ()).throw(exc),
                       sleep=lambda _: self.fail("unexpected retry"))
        self.assertEqual(result["http_status"], 403)
        self.assertEqual(result["http_reason"], "Forbidden")
        self.assertEqual(result["rate_limit_remaining"], "0")

    def test_http_429_honors_bounded_retry_after(self):
        calls, sleeps = [], []
        def fetch(_url):
            calls.append(1)
            if len(calls) == 1:
                raise urllib.error.HTTPError("https://codeberg.org/api/v1/repos/search", 429,
                                             "rate limited", {"Retry-After": "17"}, None)
            return {"data": []}
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(sleeps, [17])

    def test_http_429_honors_http_date_retry_after(self):
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=35)
        header = format_datetime(retry_at, usegmt=True)
        sleeps = []
        def fetch(_url):
            raise urllib.error.HTTPError("https://codeberg.org/api/v1/repos/search", 429,
                                         "rate limited", {"Retry-After": header}, None)
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["reason"], "HTTP_429")
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(all(0 <= delay <= 35 for delay in sleeps))
        self.assertTrue(all(delay >= 30 for delay in sleeps))

    def test_http_429_retry_after_is_capped(self):
        calls, sleeps = [], []
        def fetch(_url):
            calls.append(1)
            raise urllib.error.HTTPError("https://gitlab.com/api/v4/projects", 429,
                                         "rate limited", {"Retry-After": "9999"}, None)
        result = probe("gitlab", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["reason"], "HTTP_429")
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(sleeps, [60, 60])

    def test_http_429_without_header_uses_exponential_backoff(self):
        calls, sleeps = [], []
        def fetch(_url):
            calls.append(1)
            raise http_error(429)
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["reason"], "HTTP_429")
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(sleeps, [30, 60])


    def test_http_date_retry_after_is_honored_and_capped(self):
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime
        calls, sleeps = [], []
        future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=180), usegmt=True)
        def fetch(_url):
            calls.append(1)
            if len(calls) == 1:
                raise urllib.error.HTTPError("https://codeberg.org/api/v1/repos/search", 429,
                                             "rate limited", {"Retry-After": future}, None)
            return {"data": []}
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [60])

    def test_past_http_date_retry_after_does_not_sleep(self):
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime
        calls, sleeps = [], []
        past = format_datetime(datetime.now(timezone.utc) - timedelta(seconds=30), usegmt=True)
        def fetch(_url):
            calls.append(1)
            if len(calls) == 1:
                raise urllib.error.HTTPError("https://codeberg.org/api/v1/repos/search", 429,
                                             "rate limited", {"Retry-After": past}, None)
            return {"data": []}
        result = probe("codeberg", fetch=fetch, sleep=sleeps.append)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(sleeps, [0])

if __name__ == "__main__":
    unittest.main()
