#!/usr/bin/env python3
"""Bulk offline contract tests for configured IPTV and forge adapters."""
import json
import pathlib
import unittest
from urllib.parse import urlsplit
from forge_source_review import normalize
from forge_source_discovery import gitlab_projects, codeberg_projects, playlist_sources, parse_tree_paths

ROOT = pathlib.Path(__file__).resolve().parent

class SourceAdapterMatrix(unittest.TestCase):
    def test_configured_iptv_and_gist_sources(self):
        sources = json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8"))["sources"]
        ids = [x["id"] for x in sources]
        self.assertEqual(len(ids), len(set(ids)))
        for required in ("iptv-org", "iptv-org-tr", "iptv-org-az", "iptv-org-tur-language", "iptv-org-aze-language", "free-tv-independent", "akan1970-newlisttr"):
            self.assertIn(required, ids)
        for source in sources:
            self.assertEqual(urlsplit(source["url"]).scheme, "https")
            self.assertIn(source["scope"], ("TR", "AZ", "world", "SE", "candidate"))

    def test_gitlab_tree_to_approved_source(self):
        projects = gitlab_projects([{"id": 42, "default_branch": "main"}])
        self.assertEqual(len(projects), 1)
        paths = parse_tree_paths([{"type": "blob", "path": "tv/tr.m3u"}])
        url = playlist_sources(projects[0], paths)[0]
        self.assertEqual(normalize({"schema": 1, "sources": [{"forge": "gitlab", "source_url": url} ]})[0]["url"], url)

    def test_codeberg_tree_to_approved_source(self):
        projects = codeberg_projects({"data": [{"owner": {"login": "example"}, "name": "tv", "default_branch": "main"}]})
        self.assertEqual(len(projects), 1)
        url = playlist_sources(projects[0], ["tr.m3u"])[0]
        self.assertEqual(normalize({"schema": 1, "sources": [{"forge": "codeberg", "source_url": url}]})[0]["url"], url)

    def test_forge_review_requires_valid_schema(self):
        with self.assertRaises(ValueError):
            normalize({"schema": 999, "sources": []})

if __name__ == "__main__":
    unittest.main()
