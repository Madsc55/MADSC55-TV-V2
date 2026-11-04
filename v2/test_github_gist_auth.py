#!/usr/bin/env python3
"""Offline regression: public Gist metadata is not queried with a CI app token."""
import io
import json
import os
import unittest
from unittest.mock import patch

from github_source_discovery import api


class FakeOpener:
    def __init__(self):
        self.headers = []
    def open(self, request, timeout=18):
        self.headers.append(dict(request.header_items()))
        return io.BytesIO(json.dumps([]).encode("utf-8"))


class PublicGistAuthorizationTests(unittest.TestCase):
    def test_public_user_gists_use_anonymous_access_with_ci_token(self):
        opener = FakeOpener()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ci-app-token"}), \
                patch("urllib.request.build_opener", return_value=opener):
            result = api("https://api.github.com/users/sample-user/gists?per_page=30")
        self.assertEqual(result, [])
        self.assertEqual(len(opener.headers), 1)
        self.assertNotIn("Authorization", opener.headers[0])

    def test_repository_search_remains_authenticated(self):
        opener = FakeOpener()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ci-app-token"}), \
                patch("urllib.request.build_opener", return_value=opener):
            api("https://api.github.com/search/repositories?q=iptv")
        self.assertEqual(opener.headers[0].get("Authorization"), "Bearer ci-app-token")

    def test_api_rejects_non_github_hosts_before_network(self):
        opener = FakeOpener()
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(ValueError):
                api("https://example.com/users/sample-user/gists")
        self.assertEqual(opener.headers, [])


if __name__ == "__main__":
    unittest.main()
