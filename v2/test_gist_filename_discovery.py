#!/usr/bin/env python3
"""Gist source path screening regression without external requests."""
import unittest
from github_source_discovery import eligible_playlist_path


class GistFilenameTests(unittest.TestCase):
    def test_m3u_filename_regex_matches(self):
        for filename in ("tr.m3u", "az.m3u8", "iptv.txt", "tv-playlist.txt"):
            with self.subTest(filename=filename):
                self.assertTrue(eligible_playlist_path(filename))
        for filename in ("tr.json", "README.txt", "secrets.txt", "../bad.m3u",
                         "/private.m3u", "folder\\bad.m3u", "playlist.exe"):
            with self.subTest(filename=filename):
                self.assertFalse(eligible_playlist_path(filename))


if __name__ == "__main__":
    unittest.main(verbosity=2)
