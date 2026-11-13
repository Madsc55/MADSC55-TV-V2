#!/usr/bin/env python3
"""Offline regression for bounded #34 live metadata retries."""
import unittest
import urllib.error
from discovery_34_live_contract import probe

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

    def test_malformed_provider_payload_fails_closed(self):
        for provider, malformed in (("github", []), ("gitlab", {}), ("codeberg", None)):
            with self.subTest(provider=provider):
                result = probe(provider, fetch=lambda _url, value=malformed: value,
                               sleep=lambda _: self.fail("unexpected sleep"))
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["reason"], "ValueError")
                self.assertEqual(result["attempts"], 1)

    def test_exhaustion_fails_closed(self):
        result = probe("codeberg", fetch=lambda _: (_ for _ in ()).throw(http_error(429)), sleep=lambda _: None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["attempts"], 3)
        self.assertTrue(result["retryable"])

if __name__ == "__main__":
    unittest.main()
