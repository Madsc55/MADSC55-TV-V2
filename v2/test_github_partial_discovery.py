#!/usr/bin/env python3
"""GitHub/Gist discovery retains partial audit on API outages, without network."""
import json
import tempfile
import pathlib
import unittest
from unittest.mock import patch
import github_source_discovery as discovery

class GitHubPartialTests(unittest.TestCase):
    def test_api_failure_is_recorded_without_dropping_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / "sources.json"
            report = root / "report.json"
            config.write_text('{"sources":[]}', encoding="utf-8")
            with patch.object(discovery, "CONFIG", config), \
                 patch.object(discovery, "OUT", report), \
                 patch.object(discovery, "QUERIES", ["turkish iptv m3u"]), \
                 patch.object(discovery, "api", side_effect=OSError("rate limit")):
                discovery.main()
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["coverage_status"], "PARTIAL_API_ERRORS")
            self.assertEqual(len(payload["errors"]), 1)
            self.assertEqual(payload["sources_found"], 0)
            self.assertIs(payload["playback_verified"], False)
            self.assertNotIn("rate limit", report.read_text(encoding="utf-8"))
if __name__ == "__main__":
    unittest.main(verbosity=2)
