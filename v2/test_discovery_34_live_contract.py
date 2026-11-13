#!/usr/bin/env python3
"""Offline regression for bounded #34 live metadata retries."""
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import urllib.error
from discovery_34_live_contract import probe, retry_delay

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
        self.assertEqual(sleeps, [5, 10])


    def test_http_date_retry_after_is_parsed(self):
        value = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=20), usegmt=True)
        error = urllib.error.HTTPError("https://codeberg.org/api/v1/repos/search", 429, "limited", {"Retry-After": value}, None)
        delay = retry_delay(error, 1)
        self.assertGreaterEqual(delay, 0)
        self.assertLessEqual(delay, 20)

    def test_http_date_retry_after_is_capped(self):
        value = format_datetime(datetime.now(timezone.utc) + timedelta(hours=2), usegmt=True)
        error = urllib.error.HTTPError("https://gitlab.com/api/v4/projects", 429, "limited", {"Retry-After": value}, None)
        self.assertEqual(retry_delay(error, 1), 60)

    def test_past_http_date_retries_immediately(self):
        value = format_datetime(datetime.now(timezone.utc) - timedelta(seconds=10), usegmt=True)
        error = urllib.error.HTTPError("https://codeberg.org/api/v1/repos/search", 429, "limited", {"Retry-After": value}, None)
        self.assertEqual(retry_delay(error, 1), 0)

if __name__ == "__main__":
    unittest.main()
