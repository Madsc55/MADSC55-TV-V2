import json
import tempfile
import unittest
from pathlib import Path
from discovery_34_integrate import integrate, normalize

class IntegrationTests(unittest.TestCase):
    def test_all_six_existing_formats(self):
        self.assertEqual(len(normalize("official", {"channels": [{"official_site": "https://example.org"}]})), 1)
        self.assertEqual(len(normalize("youtube", {"results": [{"video_id": "AbCdEf12345"}]})), 1)
        self.assertEqual(len(normalize("m3u", {"sources": [{"kind": "m3u", "url": "https://example.org/tr.m3u"}]})), 1)
        self.assertEqual(len(normalize("github_m3u", {"sources": [{"status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED", "url": "https://raw.githubusercontent.com/a/b/main/tr.m3u"}]})), 1)
        for provider in ("gitlab_m3u", "codeberg_m3u"):
            self.assertEqual(len(normalize(provider, {"sources": [{"status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED", "url": "https://example.org/tr.m3u"}]})), 1)
    def test_official_and_youtube_metadata_survive_integration(self):
        official = normalize("official", {"channels": [{
            "official_site": "https://tv.example/live", "name": "Example TV",
            "channel_id": "example.tv", "country": "GB",
            "status": "DIRECTORY_REFERENCE_ONLY_NOT_STREAM_VERIFIED"}]})[0]
        youtube = normalize("youtube", {"results": [{
            "video_id": "AbCdEf12345", "title": "Live News",
            "channel": "News Channel", "region": "WORLD", "status": "LIVE_METADATA_VERIFIED"}]})[0]
        self.assertEqual(official["name"], "Example TV")
        self.assertEqual(official["tvg_id"], "example.tv")
        self.assertEqual(official["country"], "GB")
        self.assertEqual(youtube["name"], "Live News")
        self.assertEqual(youtube["group"], "News Channel")
        self.assertEqual(youtube["status"], "LIVE_METADATA_VERIFIED")
        self.assertEqual(youtube["region"], "WORLD")

    def test_integrated_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as d:
            reports = {}
            data = {"official": {"channels": [{"official_site": "https://example.org"}]},
                    "youtube": {"results": [{"video_id": "AbCdEf12345"}, {"video_id": "AbCdEf12345"}]},
                    "m3u": {"sources": [{"kind": "m3u", "url": "https://example.org/tr.m3u"}]},
                    "github_m3u": {"sources": [{"status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED", "url": "https://raw.githubusercontent.com/a/b/main/tr.m3u"}]},
                    "gitlab_m3u": {"sources": [{"status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED", "url": "https://gitlab.com/a/b/-/raw/main/tr.m3u"}]},
                    "codeberg_m3u": {"sources": [{"status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED", "url": "https://codeberg.org/a/b/raw/branch/main/tr.m3u"}]}}
            for source, value in data.items():
                path = Path(d) / (source + ".json")
                path.write_text(json.dumps(value))
                reports[source] = path
            result = integrate(reports)
            self.assertEqual(len(result["candidates"]), 6)
            self.assertEqual(result["verified_av"], 0)
            self.assertEqual(result["errors"], [])
    def test_malformed_rows_do_not_discard_valid_candidates(self):
        fixtures = [("official", "channels", "official_site", "https://example.org"),
                    ("youtube", "results", "video_id", "AbCdEf12345"),
                    ("m3u", "sources", "url", "https://example.org/tr.m3u"),
                    ("github_m3u", "sources", "url", "https://raw.githubusercontent.com/a/b/main/tr.m3u"),
                    ("gitlab_m3u", "sources", "url", "https://gitlab.com/a/b/-/raw/main/tr.m3u"),
                    ("codeberg_m3u", "sources", "url", "https://codeberg.org/a/b/raw/branch/main/tr.m3u")]
        for source, key, field, value in fixtures:
            good = {field: value}
            if source == "m3u":
                good["kind"] = "m3u"
            if source in ("github_m3u", "gitlab_m3u", "codeberg_m3u"):
                good["status"] = "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"
            self.assertEqual(len(normalize(source, {key: [None, 17, [], good]})), 1)
            with self.assertRaises(ValueError):
                normalize(source, {key: "invalid"})

    def test_integrated_cli_preserves_existing_discovery_report(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "original.json"
            output.write_text("KEEP_EXISTING_REPORT", encoding="utf-8")
            proc = subprocess.run([sys.executable,
                str(Path(__file__).with_name("discovery_34_integrate.py")),
                "--output", str(output)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP_EXISTING_REPORT")

    def test_missing_report_is_reported(self):
        result = integrate({"youtube": Path("/nonexistent/discovery34.json")})
        self.assertEqual(len(result["errors"]), 1)

if __name__ == "__main__":
    unittest.main()
