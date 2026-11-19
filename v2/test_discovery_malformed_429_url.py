"""Regression: a malformed provider URL cannot crash bounded HTTP 429 retry."""
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discovery_provider_requests import retry_delay


class MalformedProviderUrlTests(unittest.TestCase):
    def test_429_malformed_ipv6_url_uses_bounded_provider_backoff(self):
        error = urllib.error.HTTPError("https://[bad", 429, "Too Many Requests", {}, None)
        self.assertEqual(retry_delay(error, 1), 30)
        self.assertEqual(retry_delay(error, 2), 60)
        self.assertEqual(retry_delay(error, 3), 120)

    def test_github_429_keeps_stricter_backoff(self):
        error = urllib.error.HTTPError("https://api.github.com/search/code", 429, "Too Many Requests", {}, None)
        self.assertEqual(retry_delay(error, 1), 60)
        self.assertEqual(retry_delay(error, 2), 120)
        self.assertIsNone(retry_delay(error, 3))


if __name__ == "__main__":
    unittest.main()
