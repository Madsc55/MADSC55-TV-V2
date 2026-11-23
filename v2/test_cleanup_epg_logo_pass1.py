"""Offline regression checks for pass1 cleanup (no network)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("cleanup_epg_logo_pass1.py")

class Pass1Test(unittest.TestCase):
    def test_dedupe_and_metadata_from_exact_url_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "in.m3u8"
            source.write_text(
                '#EXTM3U\n'
                '#EXTINF:-1 group-title="YEDEKLER",Alpha\nhttps://example.org/a\n'
                '#EXTINF:-1 tvg-id="alpha.id" tvg-logo="https://example.org/logo.png" group-title="YEDEKLER",Alpha copy\nhttps://example.org/a\n'
                '#EXTINF:-1 group-title="ANA ARŞİV",Beta\nhttps://example.org/b\n',
                encoding="utf-8")
            out = root / "out.m3u8"
            report = root / "report.json"
            subprocess.run([sys.executable, str(SCRIPT), "--playlist", str(source),
                            "--output", str(out), "--report", str(report)],
                           check=True, capture_output=True, text=True)
            data = report.read_text(encoding="utf-8")
            result = out.read_text(encoding="utf-8")
            self.assertEqual(json.loads(data)["duplicates_removed"], 1)
            self.assertEqual(json.loads(data)["epg_added"], 1)
            self.assertEqual(json.loads(data)["logos_added"], 1)
            self.assertEqual(result.count("#EXTINF:"), 2)
            self.assertIn('tvg-id="alpha.id"', result)
            self.assertIn('group-title="ANA ARŞİV",Beta', result)

if __name__ == "__main__":
    unittest.main()
