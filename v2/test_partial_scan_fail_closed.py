#!/usr/bin/env python3
"""Offline tests that partial public discovery never appears as success."""
import unittest
from unittest.mock import patch
import github_source_discovery as gh
import run_forge_source_discovery as forge

class PartialScanTests(unittest.TestCase):
    def test_forge_main_fails_on_partial_result(self):
        with patch.object(forge, "scan", return_value={"schema": 1, "sources": [],
                  "errors": [{"forge": "gitlab", "error": "TimeoutError"}]}), \
             patch("pathlib.Path.write_text", return_value=0), \
             patch("pathlib.Path.mkdir", return_value=None), \
             patch("sys.argv", ["scan", "--scan-public-forges"]):
            with self.assertRaisesRegex(SystemExit, "incomplete"):
                forge.main()
if __name__ == "__main__":
    unittest.main(verbosity=2)
