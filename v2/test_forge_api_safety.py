#!/usr/bin/env python3
"""Offline tests for strict public forge API host and redirect policy."""
import unittest
from unittest.mock import patch
from run_forge_source_discovery import api_json

class ForgeApiSafetyTests(unittest.TestCase):
    def test_untrusted_hosts_fail_before_network(self):
        with patch("urllib.request.build_opener", side_effect=AssertionError("network")):
            for url in ("https://localhost/api/v1/repos/search",
                        "http://gitlab.com/api/v4/projects",
                        "https://user:pass@gitlab.com/api/v4/projects",
                        "https://gitlab.com:8080/api/v4/projects",
                        "https://example.org/api/v4/projects"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    api_json(url)
    def test_allowed_forge_api_reaches_opener(self):
        with patch("urllib.request.build_opener", side_effect=RuntimeError("validated")):
            for url in ("https://gitlab.com/api/v4/projects?search=iptv",
                        "https://codeberg.org/api/v1/repos/search?q=iptv"):
                with self.subTest(url=url), self.assertRaisesRegex(RuntimeError, "validated"):
                    api_json(url)
if __name__ == "__main__":
    unittest.main(verbosity=2)
