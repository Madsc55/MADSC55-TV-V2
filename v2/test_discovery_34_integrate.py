import json
import tempfile
import unittest
from pathlib import Path
from discovery_34_integrate import integrate, normalize

class IntegrationTests(unittest.TestCase):
    def test_all_three_existing_formats(self):
        self.assertEqual(len(normalize("official", {"channels": [{"official_site": "https://example.org"}]})), 1)
        self.assertEqual(len(normalize("youtube", {"results": [{"video_id": "AbCdEf12345"}]})), 1)
        self.assertEqual(len(normalize("m3u", {"sources": [{"kind": "m3u", "url": "https://example.org/tr.m3u"}]})), 1)
    def test_integrated_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as d:
            reports = {}
            data = {"official": {"channels": [{"official_site": "https://example.org"}]},
                    "youtube": {"results": [{"video_id": "AbCdEf12345"}, {"video_id": "AbCdEf12345"}]},
                    "m3u": {"sources": [{"kind": "m3u", "url": "https://example.org/tr.m3u"}]}}
            for source, value in data.items():
                path = Path(d) / (source + ".json")
                path.write_text(json.dumps(value))
                reports[source] = path
            result = integrate(reports)
            self.assertEqual(len(result["candidates"]), 3)
            self.assertEqual(result["verified_av"], 0)
            self.assertEqual(result["errors"], [])
    def test_missing_report_is_reported(self):
        result = integrate({"youtube": Path("/nonexistent/discovery34.json")})
        self.assertEqual(len(result["errors"]), 1)

if __name__ == "__main__":
    unittest.main()
