#!/usr/bin/env python3
"""No-network GitHub API source discovery safety regression tests."""
import unittest
from unittest.mock import patch
from github_source_discovery import api

class GithubSourceSafetyTests(unittest.TestCase):
    def test_reject_untrusted_api_before_network(self):
        with patch("urllib.request.build_opener", side_effect=AssertionError("network")):
            for url in ("http://api.github.com/search/repositories",
                        "https://localhost/search/repositories",
                        "https://api.github.com:8443/search/repositories",
                        "https://user:pass@api.github.com/search/repositories",
                        "https://github.com/search/repositories"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    api(url)
    def test_allow_github_api_host(self):
        with patch("urllib.request.build_opener", side_effect=RuntimeError("validated")):
            with self.assertRaisesRegex(RuntimeError, "validated"):
                api("https://api.github.com/search/repositories?q=iptv")
if __name__ == "__main__":
    unittest.main(verbosity=2)
