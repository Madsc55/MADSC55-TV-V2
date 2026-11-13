import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request
from discovery_34 import QUERIES, SOURCES, identity, search_url, repository_candidates, curated_candidates

class Discovery34Tests(unittest.TestCase):
    def test_redirect_rejected_before_following(self):
        from discovery_34 import _NoRedirect
        handler = _NoRedirect()
        request = urllib.request.Request("https://codeberg.org/api/v1/repos/search")
        with self.assertRaisesRegex(ValueError, "Redirect refused"):
            handler.redirect_request(request, None, 302, "Found",
                                     {"Location": "http://127.0.0.1/private"},
                                     "http://127.0.0.1/private")

    def test_fetch_uses_no_redirect_handler(self):
        from discovery_34 import fetch_json, _NoRedirect
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return "https://codeberg.org/api/v1/repos/search"
            @property
            def url(self): return self.geturl()
            def read(self, n): return b'{"data":[]}'
        def opener(handler):
            self.assertIs(handler, _NoRedirect)
            return FakeOpener()
        # Capture test assertion in the outer scope.
        outer = self
        class FakeOpener:
            def open(self, req, timeout):
                outer.assertEqual(timeout, 15)
                return FakeResponse()
        with patch("discovery_34.urllib.request.build_opener", side_effect=opener):
            self.assertEqual(fetch_json("https://codeberg.org/api/v1/repos/search"), {"data": []})

    def test_sources(self):
        self.assertEqual(len(SOURCES), 6)
        self.assertIn("tr.m3u8", QUERIES)
    def test_search(self):
        for source in ("github", "gitlab", "codeberg"):
            self.assertIn("turkiye.m3u", __import__("urllib.parse", fromlist=["unquote"]).unquote(search_url(source, "turkiye.m3u")))
    def test_repositories(self):
        cases = [("github", {"items": [{"html_url": "https://github.com/a/b"}]}),
                 ("gitlab", [{"web_url": "https://gitlab.com/a/b"}]),
                 ("codeberg", {"data": [{"html_url": "https://codeberg.org/a/b"}]})]
        for source, payload in cases:
            self.assertFalse(repository_candidates(source, payload)[0]["verified_av"])
    def test_non_string_repository_url_is_skipped(self):
        for source, payload in (
            ("github", {"items": [{"html_url": None}, {"html_url": 123}]}),
            ("gitlab", [{"web_url": None}, {"web_url": ["bad"]}]),
            ("codeberg", {"data": [{"html_url": {"bad": "url"}}]}),
        ):
            with self.subTest(source=source):
                self.assertEqual(repository_candidates(source, payload), [])

    def test_malformed_curated_records_are_skipped(self):
        for source in ("official", "youtube", "m3u"):
            with self.subTest(source=source):
                records = [None, "invalid", {"url": None}, {"url": 123},
                           {"video_id": None}, {"video_id": 123}]
                self.assertEqual(curated_candidates(source, records), [])

    def test_signed_stream_query_variants_have_distinct_private_ids(self):
        for source in ("official", "m3u"):
            first = identity(source, "https://example.org/live.m3u8?token=SECRET_A")
            second = identity(source, "https://example.org/live.m3u8?token=SECRET_B")
            self.assertNotEqual(first["source_id"], second["source_id"])
            self.assertNotIn("SECRET_A", first["source_id"])
            self.assertNotIn("SECRET_B", second["source_id"])
            self.assertFalse(first["verified_av"])
            self.assertFalse(second["verified_av"])

    def test_integrated_reports_skip_malformed_rows_but_keep_valid(self):
        from discovery_34_integrate import normalize
        fixtures = (
            ("official", {"channels": [None, {"official_site": "https://example.org/tv"}]}),
            ("youtube", {"results": [42, {"video_id": "AbCdEf12345"}]}),
            ("m3u", {"sources": ["invalid", {"kind": "m3u", "url": "https://example.org/a.m3u"}]}),
        )
        for source, data in fixtures:
            with self.subTest(source=source):
                self.assertEqual(len(normalize(source, data)), 1)
        for source, key in (("official", "channels"), ("youtube", "results"), ("m3u", "sources")):
            with self.subTest(source=source), self.assertRaises(ValueError):
                normalize(source, {key: {"bad": "rows"}})

    def test_control_characters_and_invalid_url_types_rejected(self):
        for source in ("official", "m3u"):
            for url in ("https://example.org/a.m3u8\\n#EXTINF", "https://example.org/a\\rnext",
                        "https://example.org/a\\x00", "https://example.org/a\\x7f", None, 123):
                with self.subTest(source=source, url=url), self.assertRaises(ValueError):
                    identity(source, url)

    def test_youtube(self):
        items = curated_candidates("youtube", [{"video_id": "AbCdEf12345"}])
        self.assertEqual(items[0]["source_id"], "youtube:AbCdEf12345")
    def test_invalid(self):
        for url in ("file:///tmp/a", "https://localhost/a", "https://user:pass@site.org/a", "http://127.0.0.1/a", "http://192.168.1.1/a", "http://[::1]/a"):
            with self.assertRaises(ValueError):
                identity("m3u", url)
    def test_malformed_port_rejected(self):
        for url in ("https://example.org:bad/live.m3u8", "https://example.org:99999/live.m3u8"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                identity("m3u", url)

    def test_trailing_dot_hostname_canonical_identity(self):
        normal = identity("m3u", "https://example.org/live.m3u8")
        dotted = identity("m3u", "https://example.org./live.m3u8")
        self.assertEqual(normal["source_id"], dotted["source_id"])

    def test_provider_host_boundaries(self):
        for source, url in (("github", "https://github.com.evil.example/a"),
                            ("gitlab", "http://gitlab.com/a"),
                            ("codeberg", "https://example.org/a"),
                            ("youtube", "https://youtu.be/AbCdEf12345")):
            with self.assertRaises(ValueError):
                identity(source, url)
    def test_curated_cli_offline_all_three_adapters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "curated.json"
            output = root / "candidates.json"
            source.write_text(json.dumps({
                "official": [{"url": "https://example.org/official"}],
                "youtube": [{"video_id": "AbCdEf12345"}],
                "m3u": [{"url": "https://example.org/channels.m3u"}]
            }), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("discovery_34.py")),
                 "--curated-input", str(source), "--output", str(output)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual({c["source"] for c in report["candidates"]},
                             {"official", "youtube", "m3u"})
            self.assertEqual(report["mode"], "offline")
            self.assertEqual(report["av_verified"], 0)

    def test_curated_cli_rejects_unrecognized_adapters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "invalid.json"
            output = root / "candidates.json"
            source.write_text('{"unexpected": []}', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("discovery_34.py")),
                 "--curated-input", str(source), "--output", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_curated_cli_does_not_overwrite_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            output = root / "protected-report.json"
            output.write_text("DO_NOT_OVERWRITE", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("discovery_34.py")),
                 "--output", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "DO_NOT_OVERWRITE")

    def test_integrated_cli_does_not_overwrite_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            output = root / "protected-integrated.json"
            output.write_text("DO_NOT_OVERWRITE", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("discovery_34_integrate.py")),
                 "--output", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "DO_NOT_OVERWRITE")

    def test_official_and_m3u(self):
        for source in ("official", "m3u"):
            self.assertEqual(len(curated_candidates(source, [{"url": "https://example.org/live.m3u8"}])), 1)

if __name__ == "__main__":
    unittest.main()
