#!/usr/bin/env python3
"""Offline scanner regression tests: no HTTP requests, no protected playlist edits."""
import io
import json
import pathlib
from datetime import datetime, timezone
import tempfile
import unittest
from unittest.mock import patch
import real_ibo_scan as scanner

class ScannerOfflineTests(unittest.TestCase):
    def test_xmltv_epg_is_not_satisfied_by_channel_declaration_only(self):
        now = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
        xmltv = (b'<tv><channel id="match.tr"/><channel id="empty.tr"/>'
                 b'<channel id="dup.tr"/><channel id="dup.tr"/>'
                 b'<channel id="old.tr"/><channel id="untitled.tr"/>'
                 b'<programme channel="match.tr" start="20261114100000 +0000" '
                 b'stop="20261114110000 +0000"><title>News</title></programme>'
                 b'<programme channel="dup.tr" start="20261114100000 +0000" '
                 b'stop="20261114110000 +0000"><title>Fake</title></programme>'
                 b'<programme channel="undeclared.tr" start="20261114100000 +0000" '
                 b'stop="20261114110000 +0000"><title>Fake</title></programme>'
                 b'<programme channel="old.tr" start="20200101000000 +0000" '
                 b'stop="20200101010000 +0000"><title>Old</title></programme>'
                 b'<programme channel="untitled.tr" start="20261114100000 +0000" '
                 b'stop="20261114110000 +0000"/></tv>')
        self.assertEqual(scanner.validated_xmltv_programme_ids(xmltv, now=now),
                         {"match.tr"})

    def test_xmltv_rejects_dtd_invalid_root_and_wrong_time_intervals(self):
        now = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
        bad = (
            b'<!DOCTYPE tv [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><tv></tv>',
            b'<something />',
        )
        for payload in bad:
            with self.subTest(payload=payload[:15]):
                with self.assertRaises(ValueError):
                    scanner.validated_xmltv_programme_ids(payload, now=now)
        self.assertEqual(scanner.validated_xmltv_programme_ids(
            b'<tv><channel id="x"/>'
            b'<programme channel="x" start="20261114120000 +0000" '
            b'stop="20261114110000 +0000"><title>Bad</title></programme></tv>',
            now=now), set())
        self.assertEqual(scanner.validated_xmltv_programme_ids(
            b'<tv><channel id="x"/>'
            b'<programme channel="x" start="20261114120000 +1500" '
            b'stop="20261114130000 +1500"><title>Bad</title></programme></tv>',
            now=now), set())

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
        self.assertFalse(scanner.current_decode_confirmed(accepted, "AV_VERIFIED", reused=True))
        for row, status in (
                ({}, "AV_VERIFIED"),
                ({"decoded_av_verified": "true", "decode_status": "DECODED_AV"}, "AV_VERIFIED"),
                ({"decoded_av_verified": True, "decode_status": "NO_DECODED_FRAME"}, "AV_VERIFIED"),
                (accepted, "UNVERIFIED_OR_FAILED"),
                (None, "AV_VERIFIED")):
            with self.subTest(row=row, status=status):
                self.assertFalse(scanner.current_decode_confirmed(row, status))

    def test_nonstandard_network_http_status_does_not_crash_recovery(self):
        """Real feeds can respond with proxy-specific codes such as 999."""
        from stage3_recovery_queue import build_recovery_queue
        url = "https://example.org/unverified.m3u8"
        for raw in (0, 600, 999, -1, "503", True, {}, None):
            with self.subTest(http_status=raw):
                normalized = scanner.recovery_http_status(raw)
                self.assertIsNone(normalized)
                queue = build_recovery_queue([{
                    "url": url,
                    "last_http_status": normalized,
                    "recovery_attempts": 0,
                    "observations": [{"status": "UNVERIFIED_OR_FAILED"}],
                }])
                self.assertEqual(queue[0]["action"], "RETRY")
                self.assertTrue(queue[0]["preserve_history"])
        for valid in (100, 200, 206, 404, 503, 599):
            self.assertEqual(scanner.recovery_http_status(valid), valid)
        queue = build_recovery_queue([{
            "url": url,
            "last_http_status": scanner.recovery_http_status(999),
            "recovery_attempts": 3,
        }])
        self.assertEqual(queue[0]["action"], "REVIEW")

    def test_invalid_hls_url_is_not_verified(self):
        self.assertIsNone(scanner.check_hls({"url": "file:///tmp/mock.m3u8"}, 1))

    def test_historical_source_ids_preserve_both_formats(self):
        record = {"source_ids": ["new", "shared"], "source_id": "old"}
        self.assertEqual(scanner.historical_source_ids(record), ["new", "shared", "old"])
        self.assertEqual(scanner.historical_source_ids({"source_id": "old"}), ["old"])
        self.assertEqual(scanner.historical_source_ids({}), ["historical-archive"])
        with self.assertRaises(ValueError):
            scanner.historical_source_ids({"source_ids": "invalid"})

    def test_failed_recovery_queue_preserves_encrypted_av_evidence_and_baseline(self):
        """A recovery failure must not discard a multi-hour AV scan."""
        from secure_archive import decrypt
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            inventory = root / "inventory.jsonl"
            plaintext = root / "inventory.jsonl.tmp"
            report = root / "failure.json"
            baseline = root / "inventory.jsonl.enc"
            baseline.write_bytes(b"PROTECTED_PRIOR_BASELINE")
            stream_url = "https://example.org/private-token/live.m3u8"
            payload = json.dumps({
                "url": stream_url,
                "decoded_av_verified": False,
                "http_hls_status": "UNVERIFIED_OR_FAILED",
            }).encode() + b"\n"
            plaintext.write_bytes(payload)
            secret = "offline-acceptance-secret-only"
            result = scanner.preserve_failed_recovery_evidence(
                plaintext, inventory, report, secret,
                error_type="ValueError", checked=1,
                decoded_av_count=0, candidate_count=1)
            pending = root / "inventory.jsonl.pending.enc"
            self.assertEqual(decrypt(pending.read_bytes(), secret), payload)
            self.assertEqual(baseline.read_bytes(), b"PROTECTED_PRIOR_BASELINE")
            public = report.read_text(encoding="utf-8")
            self.assertNotIn(stream_url, public)
            self.assertNotIn(secret, public)
            self.assertEqual(result["status"], "RECOVERY_QUEUE_FAILED")
            self.assertEqual(result["decoded_av_verified_this_run"], 0)
            self.assertFalse(result["playback_verified_on_device"])
            self.assertTrue(result["archive_restore_test_passed"])
            with self.assertRaises(FileExistsError):
                scanner.preserve_failed_recovery_evidence(
                    plaintext, inventory, report, secret,
                    error_type="ValueError", checked=1,
                    decoded_av_count=0, candidate_count=1)
            self.assertEqual(baseline.read_bytes(), b"PROTECTED_PRIOR_BASELINE")

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

    def test_bounded_retries_skip_stale_permanent_and_success_evidence(self):
        entries = {
            "https://example.org/check-av.m3u8": {
                "result": None, "recovery_attempts": 0,
                "diagnostics": {"last_http_status": 200}},
            "https://example.org/timeout.m3u8": {
                "result": None, "recovery_attempts": 0,
                "diagnostics": {"last_timeout": True}},
            "https://example.org/transient.m3u8": {
                "result": None, "recovery_attempts": 1,
                "diagnostics": {"last_http_status": 503}},
            "https://example.org/permanent.m3u8": {
                "result": None, "recovery_attempts": 0,
                "diagnostics": {"last_http_status": 403}},
            "https://example.org/exhausted.m3u8": {
                "result": None, "recovery_attempts": 3,
                "diagnostics": {"last_http_status": 503}},
            "https://example.org/success.m3u8": {
                "result": {"decoded_av_verified": True}, "recovery_attempts": 0,
                "diagnostics": {"last_http_status": 200}},
        }
        current = {key: {} for key in entries}
        selected, eligible = scanner.select_checkpoint_retry_urls(
            entries, current, 2)
        self.assertEqual(eligible, 3)
        self.assertEqual(selected, {
            "https://example.org/check-av.m3u8",
            "https://example.org/timeout.m3u8",
        })
        self.assertEqual(scanner.select_checkpoint_retry_urls(
            entries, current, 0), (set(), 3))
        self.assertEqual(scanner.select_checkpoint_retry_urls(
            entries, current, 2000)[0],
            {"https://example.org/check-av.m3u8",
             "https://example.org/timeout.m3u8",
             "https://example.org/transient.m3u8"})
        for invalid in (-1, 2001, "300", True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    scanner.select_checkpoint_retry_urls(
                        entries, current, invalid)

    def test_retries_respect_current_candidate_inventory(self):
        prior = {"https://example.org/old.m3u8": {
            "result": None, "recovery_attempts": 0,
            "diagnostics": {"last_timeout": True}}}
        self.assertEqual(scanner.select_checkpoint_retry_urls(
            prior, {}, 100), (set(), 0))
        prior["https://example.org/old.m3u8"]["recovery_attempts"] = 4
        with self.assertRaises(ValueError):
            scanner.select_checkpoint_retry_urls(
                prior, {"https://example.org/old.m3u8": {}}, 100)

    def test_replayed_checkpoint_never_spends_an_unexecuted_recovery_attempt(self):
        for prior in range(4):
            with self.subTest(prior=prior):
                self.assertEqual(
                    scanner.next_recovery_attempts(
                        prior, reused=True, av_verified=False), prior)
                self.assertEqual(
                    scanner.next_recovery_attempts(
                        prior, reused=False, av_verified=False),
                    min(prior + 1, 3))
                self.assertEqual(
                    scanner.next_recovery_attempts(
                        prior, reused=True, av_verified=True), 0)
        self.assertEqual(scanner.observation_origin(reused=True),
                         "resumed-checkpoint")
        self.assertEqual(scanner.observation_origin(reused=False),
                         "current-scan")
        for invalid in (-1, 4, True, False, "1"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    scanner.next_recovery_attempts(
                        invalid, reused=False, av_verified=False)
        with self.assertRaises(ValueError):
            scanner.next_recovery_attempts(
                0, reused="yes", av_verified=False)

    def test_discovery_source_failures_are_explicit_and_not_mandatory(self):
        mandatory = {"configured-tr", "configured-world"}
        failed = [
            {"id": "configured-tr", "error": "HTTPError"},
            {"id": "integrated-m3u-untrusted", "error": "ValueError"},
            {"id": "github-auto-untrusted", "error": "HTTPError"},
        ]
        dropped = [
            {"id": "configured-world", "previous": 100, "current": 1},
            {"id": "integrated-m3u-small", "previous": 100, "current": 2},
        ]
        strict = scanner.classify_source_failures(
            failed, dropped, mandatory, tolerate_discovery_errors=False)
        self.assertEqual(len(strict[0]), 3)
        self.assertEqual(len(strict[1]), 0)
        self.assertEqual(len(strict[2]), 2)
        self.assertEqual(len(strict[3]), 0)
        required, optional, required_drops, optional_drops = scanner.classify_source_failures(
            failed, dropped, mandatory, tolerate_discovery_errors=True)
        self.assertEqual([item["id"] for item in required], ["configured-tr"])
        self.assertEqual([item["id"] for item in optional],
                         ["integrated-m3u-untrusted", "github-auto-untrusted"])
        self.assertEqual(required_drops[0]["id"], "configured-world")
        self.assertEqual(optional_drops[0]["id"], "integrated-m3u-small")

    def test_optional_bad_feed_does_not_fake_complete_discovery(self):
        """Keep discovery incomplete and AV unverified, without blocking mandatory intake."""
        import os
        import sys
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "v2/arsiv/yabanci_yedekler_2026-11-02_3964.m3u8"
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b"offline-fixture")
            protected = root / "protected.m3u8"
            protected.write_text(
                "#EXTM3U\n#EXTINF:-1,Protected\nhttps://example.org/protected.m3u8\n")
            sources_path = root / "sources.json"
            sources_path.write_text(json.dumps({"sources": []}))
            integrated = root / "integrated.json"
            integrated.write_text(json.dumps({"candidates": [{
                "source": "m3u", "url": "https://example.org/nonplaylist.m3u",
                "verified_av": False,
            }]}))
            report = root / "report.json"
            inventory = root / "v2/reports/ibo-candidate-inventory.jsonl"
            historic = [{"url": f"https://example.org/old/{i}"} for i in range(3964)]
            argv = [
                "real_ibo_scan.py", "--worldwide", "--live", str(protected),
                "--sources", str(sources_path), "--integrated-candidates", str(integrated),
                "--fail-fast-source-errors", "--tolerate-optional-discovery-failures",
                "--report", str(report), "--inventory", str(inventory),
            ]
            with (patch.object(scanner, "ROOT", root),
                  patch.object(scanner, "parse_m3u", return_value=iter(historic)),
                  patch.object(scanner, "fetch", side_effect=ValueError("Not M3U")) as fetch,
                  patch.object(scanner, "check_hls") as av_probe,
                  patch.object(sys, "argv", argv),
                  patch.dict(os.environ, {"V2_ARCHIVE_PASSPHRASE": "offline-passphrase-123456"})):
                scanner.main()
                fetch.assert_called_once()
                av_probe.assert_not_called()
            result = json.loads(report.read_text())
            self.assertTrue(result["configured_sources_complete"])
            self.assertTrue(result["discovery_partial"])
            self.assertFalse(result["full_discovery_acceptance"])
            self.assertEqual(len(result["optional_failed_discovered_sources"]), 1)
            self.assertEqual(result["mandatory_failed_sources"], [])
            self.assertEqual(result["status"], "PARTIAL_DISCOVERY_EVIDENCE_ONLY")
            self.assertEqual(result["av_verified"], 0)
            self.assertTrue(inventory.with_suffix(".jsonl.pending.enc").exists())
            self.assertFalse(inventory.with_suffix(".jsonl.enc").exists())
            self.assertFalse((root / "v2/reports/IBO_YENI_ADAYLAR_PART1.m3u8").exists())

    def test_failed_source_does_not_trigger_three_hour_av_scan(self):
        """A mandatory-source error must yield a truthful report before probes."""
        import os
        import sys
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "v2/arsiv/yabanci_yedekler_2026-11-02_3964.m3u8"
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b"offline-archive-fixture")
            live = root / "protected.m3u8"
            live.write_text(
                "#EXTM3U\n#EXTINF:-1,Protected\nhttps://example.org/protected.m3u8\n")
            sources = root / "sources.json"
            sources.write_text(json.dumps({"sources": [
                {"id": "unavailable", "url": "https://example.org/missing.m3u",
                 "scope": "candidate"},
            ]}))
            report_path = root / "early-report.json"
            historical = [{"url": f"https://example.org/archived/{i}"} for i in range(3964)]
            args = [
                "real_ibo_scan.py", "--worldwide",
                "--fail-fast-source-errors", "--live", str(live),
                "--sources", str(sources), "--report", str(report_path),
                "--inventory", str(root / "ibo-candidate-inventory.jsonl"),
            ]
            with (patch.object(scanner, "ROOT", root),
                  patch.object(scanner, "parse_m3u", return_value=iter(historical)),
                  patch.object(scanner, "fetch", side_effect=ValueError("Not an M3U")) as fetch,
                  patch.object(scanner, "check_hls") as av_probe,
                  patch.object(sys, "argv", args),
                  patch.dict(os.environ, {"V2_ARCHIVE_PASSPHRASE": "offline-passphrase-123456"})):
                with self.assertRaises(SystemExit) as stopped:
                    scanner.main()
                self.assertIn("Incomplete mandatory source fetch", str(stopped.exception))
                fetch.assert_called_once()
                av_probe.assert_not_called()
            result = json.loads(report_path.read_text())
            self.assertEqual(result["status"], "INCOMPLETE_SOURCE_FETCH_EARLY")
            self.assertEqual(result["failed_sources"][0]["id"], "unavailable")
            self.assertEqual(result["http_checked"], 0)
            self.assertEqual(result["av_verified"], 0)
            self.assertTrue(result["no_new_av_probes_because_source_incomplete"])
            self.assertFalse((root / "ibo-candidate-inventory.jsonl.enc").exists())

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
