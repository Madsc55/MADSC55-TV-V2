#!/usr/bin/env python3
import unittest
from forge_source_discovery import (
    gitlab_projects, codeberg_projects, playlist_sources, parse_tree_paths)

class ForgeDiscoveryTests(unittest.TestCase):
    def test_gitlab_public_project_metadata(self):
        projects = gitlab_projects([{"id": 123, "default_branch": "main"},
                                    {"id": "bad", "default_branch": "main"}])
        self.assertEqual(projects, [{"forge": "gitlab", "id": 123, "branch": "main"}])
    def test_codeberg_public_project_metadata(self):
        projects = codeberg_projects({"data": [
            {"owner": {"login": "example"}, "name": "tv", "default_branch": "main"},
            {"owner": {"login": "bad/name"}, "name": "tv", "default_branch": "main"}]})
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["owner"], "example")
    def test_explicit_playlist_files_only(self):
        p = {"forge": "codeberg", "owner": "example", "name": "tv", "branch": "main"}
        links = playlist_sources(p, ["tr.m3u", "../private.m3u", "README.md", "az.m3u8"])
        self.assertEqual(len(links), 2)
        self.assertTrue(all(x.startswith("https://codeberg.org/") for x in links))
    def test_gitlab_raw_file_encoding(self):
        p = {"forge": "gitlab", "id": 42, "branch": "main"}
        links = playlist_sources(p, ["lists/tr tv.m3u"])
        self.assertEqual(len(links), 1)
        self.assertIn("lists%2Ftr%20tv.m3u", links[0])
    def test_tree_filters(self):
        self.assertEqual(parse_tree_paths([{"type": "blob", "path": "tr.m3u"},
                                           {"type": "tree", "path": "folder"}]), ["tr.m3u"])
if __name__ == "__main__":
    unittest.main(verbosity=2)
