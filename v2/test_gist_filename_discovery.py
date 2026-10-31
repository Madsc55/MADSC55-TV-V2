#!/usr/bin/env python3
"""Gist extension recognition regression: no external requests."""
import unittest
from unittest.mock import patch
import github_source_discovery as github

class GistFilenameTests(unittest.TestCase):
    def test_m3u_filename_regex_matches(self):
        import inspect
        source = inspect.getsource(github.main)
        self.assertIn('r"(?i)\\.(m3u8?|txt)$"', source)
        import re
        for filename in ("tr.m3u", "az.m3u8", "iptv.txt"):
            self.assertTrue(re.search(r"(?i)\.(m3u8?|txt)$", filename))
        self.assertFalse(re.search(r"(?i)\.(m3u8?|txt)$", "tr.json"))
if __name__ == "__main__":
    unittest.main(verbosity=2)
