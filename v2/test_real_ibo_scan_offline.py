#!/usr/bin/env python3
"""Offline scanner regression tests: no HTTP requests, no protected playlist edits."""
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import real_ibo_scan as scanner

class ScannerOfflineTests(unittest.TestCase):
    def test_m3u_metadata_and_dedup_source(self):
        payload = (b'#EXTM3U\n'
                   b'#EXTINF:-1 tvg-id="trt1.tr" tvg-logo="https://example.org/logo.png" group-title="Haber",TRT 1\n'
                   b'https://example.org/live.m3u8\n')
        entries = list(scanner.parse_m3u(payload))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["name"], "TRT 1")
        self.assertEqual(entries[0]["tvg_id"], "trt1.tr")
        self.assertEqual(entries[0]["group"], "Haber")
        self.assertEqual(entries[0]["logo"], "https://example.org/logo.png")

    def test_reject_non_m3u(self):
        with self.assertRaises(ValueError):
            list(scanner.parse_m3u(b'not an m3u'))

    def test_scope_is_not_language_proof(self):
        record = {"name": "Unspecified TV", "group": "", "tvg_id": ""}
        self.assertTrue(scanner.tr_az(record, "TR"))
        self.assertFalse(scanner.tr_az(record, "candidate"))
        self.assertFalse(scanner.tr_az({"name": "TRT World", "group": "", "tvg_id": ""}, "TR"))

    def test_only_fresh_decoded_av_is_accepted_as_inventory_proof(self):
        accepted = {"decoded_av_verified": True, "decode_status": "DECODED_AV"}
        self.assertTrue(scanner.current_decode_confirmed(accepted, "AV_VERIFIED"))
        for row, status in (
                ({}, "AV_VERIFIED"),
                ({"decoded_av_verified": "true", "decode_status": "DECODED_AV"}, "AV_VERIFIED"),
                ({"decoded_av_verified": True, "decode_status": "NO_DECODED_FRAME"}, "AV_VERIFIED"),
                (accepted, "UNVERIFIED_OR_FAILED"),
                (None, "AV_VERIFIED")):
            with self.subTest(row=row, status=status):
                self.assertFalse(scanner.current_decode_confirmed(row, status))

    def test_invalid_hls_url_is_not_verified(self):
        self.assertIsNone(scanner.check_hls({"url": "file:///tmp/mock.m3u8"}, 1))

    def test_historical_source_ids_preserve_both_formats(self):
        record = {"source_ids": ["new", "shared"], "source_id": "old"}
        self.assertEqual(scanner.historical_source_ids(record), ["new", "shared", "old"])
        self.assertEqual(scanner.historical_source_ids({"source_id": "old"}), ["old"])
        self.assertEqual(scanner.historical_source_ids({}), ["historical-archive"])
        with self.assertRaises(ValueError):
            scanner.historical_source_ids({"source_ids": "invalid"})

    def test_dynamic_source_report_skips_malformed_rows_and_deduplicates(self):
        status = "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"
        dynamic = {"sources": [None, 3, {"url": None, "status": status},
                              {"url": "http://example.org/a.m3u", "status": status},
                              {"url": "https://example.org/a.m3u", "status": status},
                              {"url": "https://example.org/a.m3u", "status": status}]}
        accepted, rejected = scanner.normalize_dynamic_sources(dynamic, [])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["url"], "https://example.org/a.m3u")
        self.assertEqual(len(rejected), 5)

    def test_public_source_intake_refuses_private_and_malformed_hosts(self):
        invalid = (
            "https://localhost/list.m3u",
            "https://host.internal/list.m3u",
            "https://10.2.3.4/list.m3u",
            "https://127.0.0.1/list.m3u",
            "https://169.254.169.254/latest/meta-data/",
            "https://[::1]/list.m3u",
            "https://[invalid/list.m3u",
            "https://example.org:bad/list.m3u",
            "https://user:secret@example.org/list.m3u",
            "https://example.org/list.m3u#fragment",
            "https://example.org/list.m3u\\nInjected: true",
            "https://example.org/list.m3u" + chr(10) + "Injected: true",
            "http://example.org/list.m3u",
        )
        for url in invalid:
            with self.subTest(url=url):
                self.assertFalse(scanner.public_https_m3u_feed(url))
        self.assertTrue(scanner.public_https_m3u_feed("https://example.org/list.m3u?sig=opaque"))

    def test_untrusted_dynamic_and_integrated_feeds_fail_closed(self):
        status = "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"
        invalid = ["https://localhost/list.m3u", "https://10.0.0.1/a.m3u",
                   "https://[broken/a.m3u", "https://user:pw@example.org/a.m3u"]
        existing = [{"id": "already", "url": "https://example.org/already.m3u"}]
        dynamic = {"sources": ([{"url": url, "status": status} for url in invalid]
                               + [{"url": "https://example.org/already.m3u", "status": status}])}
        accepted, rejected = scanner.normalize_dynamic_sources(dynamic, existing)
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), len(invalid) + 1)
        integrated = {"candidates": [{"source": "m3u", "url": url, "verified_av": False}
                                      for url in invalid]}
        accepted, rejected = scanner.normalize_integrated_m3u_sources(integrated, [])
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), len(invalid))

    def test_private_stream_never_reaches_http_probe(self):
        for url in ("http://127.0.0.1/live.m3u8", "https://localhost/live.m3u8",
                    "https://169.254.169.254/latest/meta-data/"):
            with self.subTest(url=url):
                with patch.object(scanner.urllib.request, "urlopen") as mocked:
                    self.assertIsNone(scanner.check_hls({"url": url}, 1))
                    mocked.assert_not_called()
        self.assertTrue(scanner.public_http_stream_url("http://example.org/live.m3u8"))

    def test_main_dynamic_report_validation_runs_before_any_network(self):
        """Exercise the production CLI intake, not just its helper, offline."""
        import os
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            archive = root / "v2/arsiv/yabanci_yedekler_2026-11-02_3964.m3u8"
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b"offline-fixture")
            live = root / "protected.m3u8"
            live.write_text(chr(10).join(["#EXTM3U", "#EXTINF:-1,Protected",
                                           "https://example.org/main.m3u8"]) + chr(10))
            sources = root / "sources.json"
            sources.write_text(json.dumps({"sources": []}))
            dynamic = root / "dynamic.json"
            dynamic.write_text(json.dumps({"sources": {}}))
            records = [{"url": f"https://example.org/historical/{i}"} for i in range(3964)]
            argv = ["real_ibo_scan.py", "--live", str(live),
                    "--sources", str(sources), "--dynamic-sources", str(dynamic)]
            with (patch.object(scanner, "ROOT", root),
                  patch.object(scanner, "parse_m3u", return_value=iter(records)),
                  patch.object(scanner, "fetch") as fetch,
                  patch.object(sys, "argv", argv),
                  patch.dict(os.environ, {"V2_ARCHIVE_PASSPHRASE": "offline-only-secret-12345"}),
                  patch("sys.stderr", new_callable=io.StringIO) as error_output):
                with self.assertRaises(SystemExit) as failure:
                    scanner.main()
                self.assertEqual(failure.exception.code, 2)
                self.assertIn("Dynamic discovery report", error_output.getvalue())
                fetch.assert_not_called()

    def test_dynamic_source_report_rejects_invalid_root(self):
        for value in (None, [], {"sources": {}}, {"sources": None}):
            with self.assertRaises(ValueError):
                scanner.normalize_dynamic_sources(value, [])

    def test_archive_entry_count_not_unique_url_count(self):
        sample = (b'#EXTM3U\n#EXTINF:-1,One\nhttps://example.org/same.m3u8\n'
                  b'#EXTINF:-1,Two\nhttps://example.org/same.m3u8\n')
        entries = list(scanner.parse_m3u(sample))
        self.assertEqual(len(entries), 2)
        self.assertEqual(len({x["url"] for x in entries}), 1)

    def test_worldwide_mode_includes_entries_without_tr_az_hints(self):
        record = {"name": "International News", "group": "World", "tvg_id": "news.int"}
        self.assertFalse(scanner.eligible_entry(record, "candidate", worldwide=False))
        self.assertTrue(scanner.eligible_entry(record, "candidate", worldwide=True))
        # Explicit TR/AZ exclusions remain active only in the default filtered mode.
        excluded = {"name": "TRT World", "group": "", "tvg_id": ""}
        self.assertFalse(scanner.eligible_entry(excluded, "TR", worldwide=False))
        self.assertTrue(scanner.eligible_entry(excluded, "TR", worldwide=True))

    def test_integrated_discovery_admits_only_new_https_m3u_sources(self):
        report = {"candidates": [
            {"source": "m3u", "url": "https://lists.example.net/world.m3u", "verified_av": False},
            {"source": "m3u", "url": "http://lists.example.net/insecure.m3u", "verified_av": False},
            {"source": "youtube", "url": "https://www.youtube.com/watch?v=abcdefghijk", "verified_av": False},
            {"source": "m3u", "url": "https://lists.example.net/world.m3u", "verified_av": False},
            None,
        ]}
        existing = [{"id": "configured", "url": "https://lists.example.net/already.m3u"}]
        accepted, rejected = scanner.normalize_integrated_m3u_sources(report, existing)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["url"], "https://lists.example.net/world.m3u")
        self.assertEqual(accepted[0]["scope"], "candidate")
        self.assertEqual(len(rejected), 3)

    def test_integrated_discovery_rejects_invalid_root_and_verified_claims(self):
        for report in (None, [], {"candidates": {}}, {"candidates": None}):
            with self.assertRaises(ValueError):
                scanner.normalize_integrated_m3u_sources(report, [])
        report = {"candidates": [
            {"source": "m3u", "url": "https://lists.example.net/a.m3u", "verified_av": True},
            {"source": "m3u", "url": "https://user:pass@lists.example.net/b.m3u", "verified_av": False},
        ]}
        accepted, rejected = scanner.normalize_integrated_m3u_sources(report, [])
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), 2)

if __name__ == "__main__":
    unittest.main()
