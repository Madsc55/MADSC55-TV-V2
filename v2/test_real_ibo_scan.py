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
    def test_parse_m3u_preserves_epg_and_logo(self):
        payload = (b'#EXTM3U\\n'
                   b'#EXTINF:-1 tvg-id="trt1.tr" tvg-logo="https://example.org/logo.png" '
                   b'group-title="Turkiye",TRT 1\\n'
                   b'https://example.org/live.m3u8\\n')
        entries = list(real_ibo_scan.parse_m3u(payload))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["tvg_id"], "trt1.tr")
        self.assertEqual(entries[0]["logo"], "https://example.org/logo.png")
        self.assertEqual(entries[0]["group"], "Turkiye")

    def test_invalid_timeout_is_rejected_before_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            live = root / "protected.m3u8"
            live.write_text("#EXTM3U\\nhttps://example.org/protected.m3u8\\n", encoding="utf-8")
            with patch.object(sys, "argv", ["real_ibo_scan.py", "--live", str(live),
                                            "--timeout", "nan"]), patch.object(
                    real_ibo_scan, "fetch", side_effect=AssertionError("network called")):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        real_ibo_scan.main()

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
