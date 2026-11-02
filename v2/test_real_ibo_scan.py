#!/usr/bin/env python3
"""Regression: incomplete source coverage never overwrites an existing IBO export."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import real_ibo_scan


class PartialSourceTests(unittest.TestCase):
    def test_failed_source_preserves_existing_package_and_reports_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            live = root / "protected.m3u8"
            live.write_text("#EXTM3U\n#EXTINF:-1,Protected\nhttps://example.org/protected.m3u8\n", encoding="utf-8")
            output = root / "existing.m3u8"
            original = b"#EXTM3U\n#EXTINF:-1,Previously verified\nhttps://example.org/old.m3u8\n"
            output.write_bytes(original)
            sources = root / "sources.json"
            sources.write_text(json.dumps({"sources": [{"id": "offline", "url": "https://example.org/unreachable.m3u"}]}))
            report = root / "report.json"
            argv = ["real_ibo_scan.py", "--sources", str(sources), "--live", str(live),
                    "--output", str(output), "--report", str(report)]
            with patch.object(sys, "argv", argv), patch.object(real_ibo_scan, "fetch", side_effect=TimeoutError("offline")):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        real_ibo_scan.main()
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "PARTIAL_SOURCE_FETCH")
            self.assertFalse(data["source_coverage_complete"])
            self.assertEqual(data["failed_sources"][0]["id"], "offline")
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(live.read_text(encoding="utf-8").count("https://"), 1)


if __name__ == "__main__":
    unittest.main()
