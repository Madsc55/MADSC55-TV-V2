import unittest
import urllib.request
from discovery_34 import QUERIES, SOURCES, identity, search_url, repository_candidates, curated_candidates

class Discovery34Tests(unittest.TestCase):
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
    def test_youtube(self):
        items = curated_candidates("youtube", [{"video_id": "AbCdEf12345"}])
        self.assertEqual(items[0]["source_id"], "youtube:AbCdEf12345")
    def test_invalid(self):
        for url in ("file:///tmp/a", "https://localhost/a", "https://user:pass@site.org/a", "http://127.0.0.1/a", "http://192.168.1.1/a", "http://[::1]/a"):
            with self.assertRaises(ValueError):
                identity("m3u", url)
    def test_provider_host_boundaries(self):
        for source, url in (("github", "https://github.com.evil.example/a"),
                            ("gitlab", "http://gitlab.com/a"),
                            ("codeberg", "https://example.org/a"),
                            ("youtube", "https://youtu.be/AbCdEf12345")):
            with self.assertRaises(ValueError):
                identity(source, url)
    def test_api_redirect_is_refused_before_followup_request(self):
        from discovery_34 import _NoRedirect
        handler = _NoRedirect()
        request = urllib.request.Request("https://api.github.com/search/repositories?q=test")
        with self.assertRaisesRegex(ValueError, "Redirect refused"):
            handler.redirect_request(request, None, 302, "Found", {}, "https://example.org/redirect")

    def test_malformed_external_candidate_urls_are_skipped(self):
        for source, payload in (("github", {"items": [{"html_url": None}, {"html_url": 123}, {"html_url": "https://github.com/a/b"}]}), ("gitlab", [{"web_url": []}, {"web_url": "https://gitlab.com/a/b"}]), ("codeberg", {"data": [{"html_url": {}}, {"html_url": "https://codeberg.org/a/b"}]})):
            self.assertEqual(len(repository_candidates(source, payload)), 1)
        for source in ("official", "m3u"):
            self.assertEqual(len(curated_candidates(source, [{"url": None}, {"url": 123}, {"url": "https://example.org/live.m3u8"}])), 1)

    def test_malformed_curated_records_are_skipped(self):
        for source in ("official", "m3u", "youtube"):
            records = [None, 7, [], "not-a-record"]
            records.append({"video_id": "AbCdEf12345"} if source == "youtube" else {"url": "https://example.org/live.m3u8"})
            self.assertEqual(len(curated_candidates(source, records)), 1)

    def test_youtube_invalid_video_id_types(self):
        records = [{"video_id": None}, {"video_id": 123}, {"video_id": []}, {"video_id": {}}, {"video_id": "AbCdEf12345"}]
        self.assertEqual(len(curated_candidates("youtube", records)), 1)

    def test_control_characters_and_invalid_url_types_rejected(self):
        for source in ("official", "m3u"):
            for url in ("https://example.org/a.m3u8\n#EXTINF", "https://example.org/a\rnext", "https://example.org/a\x00", "https://example.org/a\x7f", None, 123):
                with self.subTest(source=source, url=url), self.assertRaises(ValueError):
                    identity(source, url)
            self.assertEqual(curated_candidates(source, [{"url": "https://example.org/a\n#EXTINF"}]), [])

    def test_signed_and_port_specific_stream_urls_keep_unique_safe_ids(self):
        for source in ("official", "m3u"):
            a = identity(source, "https://example.org/live.m3u8?token=SECRET_A")
            b = identity(source, "https://example.org/live.m3u8?token=SECRET_B")
            self.assertNotEqual(a["source_id"], b["source_id"])
            self.assertNotIn("SECRET_A", a["source_id"])
            self.assertNotIn("SECRET_B", b["source_id"])
            self.assertFalse(a["verified_av"])
        standard = identity("m3u", "https://example.org/live.m3u8")
        alternate = identity("m3u", "https://example.org:8443/live.m3u8")
        self.assertNotEqual(standard["source_id"], alternate["source_id"])
        self.assertIn(":8443", alternate["source_id"])

    def test_malformed_port_fail_closed_without_dropping_valid_candidates(self):
        for url in ("https://example.org:99999/live.m3u8", "https://example.org:bad/live.m3u8"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "Invalid URL port"):
                identity("m3u", url)
        records = [{"url": "https://example.org:99999/live.m3u8"},
                   {"url": "https://example.org/live.m3u8?token=VALID"}]
        result = curated_candidates("m3u", records)
        self.assertEqual(len(result), 1)
        self.assertNotIn("VALID", result[0]["source_id"])

    def test_signed_url_queries_have_distinct_nonsecret_identities(self):
        first = identity("m3u", "https://example.org/live.m3u8?token=alpha")
        second = identity("m3u", "https://example.org/live.m3u8?token=beta")
        self.assertNotEqual(first["source_id"], second["source_id"])
        self.assertNotIn("alpha", first["source_id"])
        self.assertNotIn("beta", second["source_id"])
        self.assertEqual(identity("m3u", "https://example.org/live.m3u8")["source_id"],
                         "m3u:example.org/live.m3u8")

    def test_nondefault_ports_and_invalid_ports(self):
        plain = identity("m3u", "https://example.org/live.m3u8")["source_id"]
        port = identity("m3u", "https://example.org:8443/live.m3u8")["source_id"]
        self.assertNotEqual(plain, port)
        self.assertIn(":8443", port)
        for url in ("https://example.org:bad/live.m3u8", "https://example.org:99999/live.m3u8"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                identity("m3u", url)

    def test_cli_preserves_existing_discovery_report(self):
        import pathlib
        import subprocess
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            output = pathlib.Path(d) / "original.json"
            output.write_text("KEEP_EXISTING_REPORT", encoding="utf-8")
            proc = subprocess.run([sys.executable,
                str(pathlib.Path(__file__).with_name("discovery_34.py")),
                "--output", str(output)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "KEEP_EXISTING_REPORT")

    def test_official_and_m3u(self):
        for source in ("official", "m3u"):
            self.assertEqual(len(curated_candidates(source, [{"url": "https://example.org/live.m3u8"}])), 1)

if __name__ == "__main__":
    unittest.main()
