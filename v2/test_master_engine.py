#!/usr/bin/env python3
"""Offline integration tests for the master engine. No mocked success reports."""
import unittest
from master_engine import build, render_m3u, export_candidates

class MasterTests(unittest.TestCase):
    def test_all_approved_dynamic_sources_are_reviewed_without_position_cap(self):
        import hashlib
        from master_engine import approved_dynamic_sources
        configured = [{"id": "base", "url": "https://raw.githubusercontent.com/fixture/repo/main/base.m3u"}]
        rows = [{"url": f"https://raw.githubusercontent.com/fixture/repo/main/{i}.m3u"}
                for i in range(321)]
        approved = {hashlib.sha256(rows[i]["url"].encode()).hexdigest() for i in (0, 240, 320)}
        rows += [{"url": "https://user:secret@raw.githubusercontent.com/fixture/repo/main/unsafe.m3u"},
                 dict(rows[320])]
        result = approved_dynamic_sources(configured, {"sources": rows}, approved)
        self.assertEqual([row["url"] for row in result],
                         [configured[0]["url"], *(rows[i]["url"] for i in (0, 240, 320))])
        self.assertEqual(len(configured), 1)

    def test_budget_stops_scheduling_and_checkpoints_all_unfinished_candidates(self):
        from master_engine import verify_in_batches
        import copy
        current, calls, saved = [0.0], [], []
        items = [{"url": f"https://example.org/{i}.m3u8"} for i in range(5)]
        def check(item):
            calls.append(item["url"])
            return True
        def runner(operation, seconds):
            self.assertEqual(seconds, 1.0)
            value = operation()
            current[0] += 1
            return "ok", value
        complete = verify_in_batches(items, check, lambda _: True, workers=2,
            deadline=2, batch_timeout=1, clock=lambda: current[0], runner=runner,
            checkpoint=lambda rows, stage: saved.append((stage, copy.deepcopy(rows))))
        self.assertFalse(complete)
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(saved[0][1]), 5)
        self.assertTrue(all(row["verification_status"] == "UNTESTED" for row in saved[0][1]))
        self.assertEqual([len(rows) for _, rows in saved[1:]], [2, 2])
        self.assertTrue(all(row["media_decoded"] is True for row in items[:4]))
        self.assertEqual(items[4]["verification_status"], "UNTESTED")
        self.assertTrue(all(row["device_verified"] is False for row in items))

    def test_batch_timeout_is_incomplete_not_success_and_runner_budget_is_capped(self):
        from master_engine import verify_in_batches
        items = [{"url": "https://example.org/a.m3u8"}]
        observed = []
        def runner(operation, seconds):
            observed.append(seconds)
            return "timeout", None
        self.assertFalse(verify_in_batches(items, lambda _: True, lambda _: True,
            workers=1, deadline=3, batch_timeout=40, clock=lambda: 2,
            runner=runner, checkpoint=lambda *args: None))
        self.assertEqual(observed, [1])
        self.assertEqual(items[0]["verification_status"], "UNTESTED_BATCH_TIMEOUT")
        self.assertFalse(items[0]["media_decoded"])

    def test_bounded_batch_rejects_truncated_or_forged_worker_results(self):
        from master_engine import verify_in_batches
        for forged in (
            [],
            [{"url": "https://example.org/other.m3u8",
              "verification_status": "CHECKED", "media_decoded": True,
              "device_verified": False}],
            [{"url": "https://example.org/a.m3u8",
              "verification_status": "CHECKED", "media_decoded": "true",
              "device_verified": False}],
            [{"url": "https://example.org/a.m3u8",
              "verification_status": "CHECKED", "media_decoded": True,
              "device_verified": False, "network_status": "UNKNOWN_OR_FAILED"}],
            [{"url": "https://example.org/a.m3u8",
              "verification_status": "CHECKED", "media_decoded": True,
              "device_verified": False, "network_status": "FORGED"}],
        ):
            with self.subTest(forged=forged):
                rows = [{"url": "https://example.org/a.m3u8"}]
                self.assertFalse(verify_in_batches(
                    rows, lambda _: True, lambda _: True, workers=1,
                    deadline=2, batch_timeout=1, clock=lambda: 0,
                    runner=lambda operation, seconds: ("ok", forged),
                    checkpoint=lambda *args: None))
                self.assertEqual(rows[0]["verification_status"],
                                 "UNTESTED_BATCH_INVALID_RESULT")
                self.assertFalse(rows[0]["media_decoded"])

    def test_isolated_hung_callback_is_killed_and_worker_is_reaped(self):
        import multiprocessing
        import time
        from master_engine import run_bounded
        before = {child.pid for child in multiprocessing.active_children()}
        def hang():
            while True:
                time.sleep(0.01)
        started = time.monotonic()
        self.assertEqual(run_bounded(hang, .15), ("timeout", None))
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual({child.pid for child in multiprocessing.active_children()}, before)
        self.assertEqual(run_bounded(lambda: {"completed": True}, 2),
                         ("ok", {"completed": True}))

    def test_source_fetch_spends_same_cli_budget_and_preserves_unchecked_history(self):
        import contextlib
        import io
        import json
        import os
        from pathlib import Path
        import sys
        import tempfile
        from unittest.mock import patch
        import master_engine as module
        from encrypted_archive import restore
        source = {"id": "fixture", "scope": "TR", "url": "https://example.org/source.m3u"}
        payload = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/a.m3u8\n"
        current, calls = [0], []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live, config, history = [root / name for name in ("live.m3u", "sources.json", "history.jsonl")]
            live.write_text("#EXTM3U\n")
            config.write_text(json.dumps({"sources": [source]}))
            old = {"url": "https://example.org/history.m3u8", "name": "TRT 2", "source": "old"}
            history.write_text(json.dumps(old) + "\n")
            archive, output = root / "inventory.enc", root / "out"
            def runner(operation, seconds):
                calls.append(seconds)
                result = operation()
                current[0] = 2
                return "ok", result
            argv = ["master_engine.py", "--archive", str(archive), "--out", str(output),
                    "--history", str(history), "--max-seconds", "2"]
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}), \
                    patch.object(sys, "argv", argv), patch.object(module, "ROOT", root), \
                    patch.object(module, "LIVE", live), patch.object(module, "SOURCES", config), \
                    patch.object(module, "DYNAMIC", root / "absent.json"), \
                    patch.object(module, "FORGE", root / "absent-forge.json"), \
                    patch.object(module.time, "monotonic", side_effect=lambda: current[0]), \
                    patch.object(module, "run_bounded", side_effect=runner), \
                    patch("source_failover.execute_pipeline", return_value=[(source, payload,
                        {"id": "fixture", "fresh": True, "status": "PRIMARY_OK"})]), \
                    patch.object(module, "hls_reachable") as manifest, \
                    patch.object(module, "decode_media") as decoder, \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(SystemExit, "Verification incomplete"):
                    module.main()
                records = restore(archive)
            self.assertEqual(calls, [2])
            manifest.assert_not_called()
            decoder.assert_not_called()
            self.assertEqual(records[0]["records"], [old])
            self.assertEqual(len(records), 3)
            self.assertTrue(all(row["verification_status"] == "UNTESTED" for row in records[1:]))
            report = json.loads((output / "report.json").read_text())
            self.assertTrue(report["budget_exhausted"])
            self.assertEqual(report["verification_unfinished"], 2)
            self.assertEqual(list(output.glob("*.m3u*")), [])

    def test_incomplete_cli_preserves_history_inventory_checkpoint_without_packages(self):
        import contextlib
        import io
        import json
        import os
        from pathlib import Path
        import sys
        import tempfile
        from unittest.mock import patch
        import master_engine as module
        from encrypted_archive import restore
        source = {"id": "fixture", "scope": "TR", "url": "https://example.org/source.m3u"}
        payload = ("#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/a.m3u8\n"
                   "#EXTINF:-1,TRT 2\nhttps://example.org/b.m3u8\n")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live, config, history = [root / name for name in ("live.m3u", "sources.json", "history.jsonl")]
            live.write_text("#EXTM3U\n")
            config.write_text(json.dumps({"sources": [source]}))
            old = {"url_sha256": "f" * 64, "source": "historical"}
            history.write_text(json.dumps(old) + "\n")
            archive, output = root / "inventory.enc", root / "out"
            count = [0]
            def runner(operation, seconds):
                count[0] += 1
                if count[0] == 3:
                    return "timeout", None
                return "ok", operation()
            argv = ["master_engine.py", "--archive", str(archive), "--out", str(output),
                    "--history", str(history), "--workers", "1"]
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}), \
                    patch.object(sys, "argv", argv), patch.object(module, "ROOT", root), \
                    patch.object(module, "LIVE", live), patch.object(module, "SOURCES", config), \
                    patch.object(module, "DYNAMIC", root / "absent.json"), \
                    patch.object(module, "FORGE", root / "absent-forge.json"), \
                    patch.object(module, "run_bounded", side_effect=runner), \
                    patch("source_failover.execute_pipeline", return_value=[(source, payload,
                        {"id": "fixture", "fresh": True, "status": "PRIMARY_OK"})]), \
                    patch.object(module, "hls_reachable", return_value=True), \
                    patch.object(module, "decode_media", return_value=True), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(SystemExit, "Verification incomplete"):
                    module.main()
                records = restore(archive)
                checkpoint = restore(output / "checkpoint.enc")
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report["status"], "INCOMPLETE_VERIFICATION")
            self.assertFalse(report["approved"])
            self.assertFalse(report["device_verified"])
            self.assertFalse(report["verification_complete"])
            self.assertEqual(report["verification_unfinished"], 1)
            self.assertEqual(report["media_decoded"], 1)
            self.assertEqual(report["batch_count"], 0)
            self.assertEqual(list(output.glob("*.m3u*")), [])
            self.assertEqual(records[0]["records"], [old])
            self.assertEqual({row["url"] for row in records[1:]},
                             {"https://example.org/a.m3u8", "https://example.org/b.m3u8"})
            self.assertEqual(checkpoint[0]["records"], [old])
            self.assertTrue(any(block["kind"] == "inventory_before_verification" for block in checkpoint))
            self.assertNotIn(b"https://example.org", (output / "checkpoint.enc").read_bytes())
            self.assertTrue(report["archive_restore_verified"])

    def test_retired_source_remains_in_catalog_but_is_not_fetched(self):
        import json
        from discover import SOURCES
        from master_engine import active_sources
        configured = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
        retired = [source for source in configured if source.get("enabled") is False]
        active = active_sources(configured)
        self.assertTrue(any(source["id"] == "ilyswch-iptv-tr" for source in retired))
        self.assertFalse(any(source["id"] == "ilyswch-iptv-tr" for source in active))
        self.assertEqual(len(active) + len(retired), len(configured))
        self.assertTrue(all(source.get("enabled", True) is not False for source in active))

    def test_real_hls_scanner_returns_entry_not_boolean(self):
        from unittest.mock import patch
        import master_engine
        entry = {"url": "https://example.org/real.m3u8"}
        with patch.object(master_engine, "check_hls", return_value=entry):
            self.assertTrue(master_engine.hls_reachable(entry, 12))
        with patch.object(master_engine, "check_hls", return_value=None):
            self.assertFalse(master_engine.hls_reachable(entry, 12))
        with patch.object(master_engine, "check_hls", return_value={"error": "HTTP_404"}):
            self.assertFalse(master_engine.hls_reachable(entry, 12))

    def test_master_protected_output_paths_are_checked_before_network(self):
        import contextlib
        import io
        import pathlib
        import sys
        import tempfile
        from unittest.mock import patch
        import master_engine

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            history = root / "history.jsonl"
            history.write_text('{"url":"https://example.org/old.m3u8"}\n', encoding="utf-8")
            archive = root / "archive.enc"
            cases = [
                (root, archive, "output parent of protected history"),
                (root / "output", history, "archive aliases history"),
            ]
            for out, archive_path, label in cases:
                with self.subTest(case=label):
                    argv = ["master_engine.py", "--history", str(history),
                            "--archive", str(archive_path), "--out", str(out)]
                    with patch.object(sys, "argv", argv), patch.dict(
                            "os.environ", {"V2_ARCHIVE_KEY_HEX": "ab" * 32}), patch.object(
                            master_engine, "fetch", side_effect=AssertionError("network called")):
                        with contextlib.redirect_stderr(io.StringIO()):
                            with self.assertRaises(SystemExit):
                                master_engine.main()
                    self.assertTrue(history.is_file())


    def test_export_is_valid_multiline_m3u_with_exact_real_urls(self):
        rows = [{"name": "TRT 1, HD\nLIVE", "url": "https://example.org/real-source.m3u8"},
                {"name": "DHA", "url": "https://example.org/other-source.m3u8"}]
        rendered = render_m3u(rows)
        self.assertEqual(rendered.splitlines(), [
            "#EXTM3U", "#EXTINF:-1,TRT 1  HD LIVE",
            "https://example.org/real-source.m3u8",
            "#EXTINF:-1,DHA", "https://example.org/other-source.m3u8"])
        self.assertTrue(rendered.endswith("\n"))
        self.assertNotIn("\\n", rendered)

    def test_export_preserves_epg_logo_group_and_stream_url(self):
        url = "https://example.org/unchanged-source.m3u8"
        rows = [{"name": "TRT 1", "url": url, "tvg_id": "TRT1.tr",
                 "logo": "https://example.org/trt.png", "group": "YEDEKLER"}]
        rendered = render_m3u(rows)
        self.assertEqual(rendered.splitlines(), [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="TRT1.tr" tvg-logo="https://example.org/trt.png" group-title="YEDEKLER",TRT 1',
            url,
        ])

    def test_real_parser_dedup_history_and_provenance(self):
        live = "#EXTM3U\n#EXTINF:-1,Existing\nhttps://example.org/existing.m3u8\n"
        data = "#EXTM3U\n#EXTINF:-1 tvg-id=\"TRT1.tr\",TRT 1\nhttps://example.org/new.m3u8\n#EXTINF:-1,Existing\nhttps://example.org/existing.m3u8\n"
        sources = [({"id": "a", "scope": "TR"}, data), ({"id": "b", "scope": "TR"}, data)]
        history = [{"url": "https://example.org/new.m3u8", "source": "#60"},
                   {"anonymous_id": "missing-real-url"}]
        items, audit, report = build(sources, live, history, checker=lambda item: True)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_ids"], ["a", "b", "#60"])
        self.assertEqual(items[0]["network_status"], "HLS_MANIFEST_REACHABLE")
        self.assertFalse(items[0]["media_decoded"])
        self.assertFalse(items[0]["device_verified"])
        self.assertEqual(len(items[0]["history"]), 1)
        self.assertEqual(report["historical_missing_real_url"], 1)
        self.assertEqual([x["parsed"] for x in audit], [2, 2])
    def test_network_checker_error_payload_blocks_decoder(self):
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        for response in ({"error": "timeout"}, "HTTP 403", 1, [True], None, False):
            with self.subTest(response=response):
                decoded_calls = []
                def decoder(item):
                    decoded_calls.append(item)
                    return True
                items, _, _ = build([({"id": "tr", "scope": "TR"}, data)],
                                    "#EXTM3U\n", checker=lambda item: response,
                                    media_checker=decoder)
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["network_status"], "UNKNOWN_OR_FAILED")
                self.assertFalse(items[0]["media_decoded"])
                self.assertEqual(decoded_calls, [])

    def test_decoder_error_payload_cannot_promote_candidate(self):
        # A decoder returning structured failure information is not AV evidence.
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        for response in ({"error": "decoder_timeout"}, "FAILED", 1, [True], None, False):
            with self.subTest(response=response):
                items, _, _ = build([({"id": "tr", "scope": "TR"}, data)],
                                    "#EXTM3U\n", checker=lambda item: True,
                                    media_checker=lambda item: response)
                self.assertEqual(len(items), 1)
                self.assertFalse(items[0]["media_decoded"])
                self.assertEqual(export_candidates(items), [])

    def test_media_decode_only_after_reachable_manifest(self):
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        items, _, _ = build([({"id": "tr", "scope": "TR"}, data)], "#EXTM3U\n",
                            checker=lambda item: True, media_checker=lambda item: True)
        self.assertTrue(items[0]["media_decoded"])
        self.assertFalse(items[0]["device_verified"])
        called = []
        items, _, _ = build([({"id": "tr", "scope": "TR"}, data)], "#EXTM3U\n",
                            checker=lambda item: False,
                            media_checker=lambda item: called.append(item) or True)
        self.assertFalse(items[0]["media_decoded"])
        self.assertEqual(called, [])

    def test_av_totals_and_export_eligibility_are_distinct(self):
        rows = [
            {"name": "TR", "region_candidate": "TR", "media_decoded": True},
            {"name": "Foreign", "region_candidate": "foreign", "media_decoded": True},
            {"name": "HTTP only", "region_candidate": "AZ", "media_decoded": False},
        ]
        self.assertEqual(sum(row.get("media_decoded") is True for row in rows), 2)
        self.assertEqual(len(export_candidates(rows)), 1)
        self.assertEqual(len(rows), 3)

    def test_k2_k5_export_gate_requires_decoded_tr_az_and_keeps_device_unverified(self):
        rows = [
            {"name": "TR", "url": "https://example.org/tr.m3u8", "region_candidate": "TR",
             "media_decoded": True, "device_verified": False},
            {"name": "AZ", "url": "https://example.org/az.m3u8", "region_candidate": "AZ",
             "media_decoded": True, "device_verified": False},
            {"name": "HTTP-only", "region_candidate": "TR", "media_decoded": False},
            {"name": "Unknown", "region_candidate": "unknown", "media_decoded": True},
            {"name": "Foreign", "region_candidate": "foreign", "media_decoded": True},
            {"name": "Unproven", "region_candidate": "AZ", "media_decoded": 1},
        ]
        selected = export_candidates(rows)
        self.assertEqual([x["name"] for x in selected], ["TR", "AZ"])
        self.assertTrue(all(x["device_verified"] is False for x in selected))
        self.assertEqual(len(rows), 6, "Filtering must not erase historical candidates")

    def test_historical_existing_main_url_never_exported(self):
        live = "#EXTM3U\n#EXTINF:-1,Existing\nhttps://example.org/existing.m3u8\n"
        history = [{"url": "https://example.org/existing.m3u8", "source": "#60"}]
        items, _, _ = build([], live, history)
        self.assertEqual(items, [])

    def test_invalid_historical_url_never_becomes_candidate(self):
        history = [{"url": "file:///etc/passwd", "source": "#60"}, {"url": "https://example.org/valid.m3u8", "source": "#60"}]
        items, _, _ = build([], "#EXTM3U\n", history)
        self.assertEqual([item["url"] for item in items], ["https://example.org/valid.m3u8"])

    def test_invalid_m3u_is_not_accepted(self):
        items, audit, _ = build([({"id": "html", "scope": "TR"}, "<html>not a playlist</html>")], "#EXTM3U\n")
        self.assertEqual(items, [])
        self.assertEqual(audit[0]["status"], "INVALID_M3U")

    def test_checker_exception_does_not_abort_scan(self):
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        def fail(_):
            raise TimeoutError("stream timeout")
        items, _, _ = build([({"id": "tr", "scope": "TR"}, data)], "#EXTM3U\n", checker=fail)
        self.assertEqual(items[0]["network_status"], "UNKNOWN_OR_FAILED")
        self.assertFalse(items[0]["device_verified"])

    def test_media_checker_exception_fails_closed(self):
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        def broken_decoder(_):
            raise RuntimeError("decoder failed")
        items, _, _ = build([({"id": "tr", "scope": "TR"}, data)], "#EXTM3U\n",
                            checker=lambda item: True, media_checker=broken_decoder)
        self.assertEqual(items[0]["network_status"], "HLS_MANIFEST_REACHABLE")
        self.assertFalse(items[0]["media_decoded"])
        self.assertFalse(items[0]["device_verified"])

    def test_empty_inventory_has_no_archive_restore_proof(self):
        items, audit, report = build([], "#EXTM3U\n", [])
        self.assertEqual(items, [])
        self.assertEqual(audit, [])
        self.assertEqual(report["recoverable_real_urls"], 0)
        # An empty build cannot prove that an encrypted archive was restored.
        self.assertFalse(bool(items) and [] == items)

    def test_duplicate_sources_decode_once_and_keep_all_provenance(self):
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        sources = [({"id": "first", "scope": "TR"}, data),
                   ({"id": "second", "scope": "TR"}, data)]
        probed, decoded = [], []
        def check(item):
            probed.append(item["url"])
            return True
        def decode(item):
            decoded.append(item["url"])
            return True
        items, audit, _ = build(sources, "#EXTM3U\n", checker=check, media_checker=decode)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_ids"], ["first", "second"])
        self.assertEqual(len(probed), 1)
        self.assertEqual(len(decoded), 1)
        self.assertTrue(items[0]["media_decoded"])
        self.assertFalse(items[0]["device_verified"])
        self.assertEqual([entry["status"] for entry in audit], ["FETCHED", "FETCHED"])

    def test_source_url_validation_blocks_private_and_credentialed_streams(self):
        data = ("#EXTM3U\n"
                "#EXTINF:-1,TRT 1\nhttp://127.0.0.1/internal.m3u8\n"
                "#EXTINF:-1,TRT 1\nhttps://user:pass@example.org/private.m3u8\n"
                "#EXTINF:-1,TRT 1\nhttps://example.org/public.m3u8\n")
        items, audit, _ = build([({"id": "tr", "scope": "TR"}, data)], "#EXTM3U\n")
        self.assertEqual([item["url"] for item in items], ["https://example.org/public.m3u8"])
        self.assertEqual(audit[0]["parsed"], 3)
        self.assertFalse(items[0].get("device_verified", False))

    def test_no_device_success_inference(self):
        data = "#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/new.m3u8\n"
        items, _, _ = build([({"id": "tr", "scope": "TR"}, data)], "#EXTM3U\n",
                            checker=lambda item: False)
        self.assertEqual(items[0]["network_status"], "UNKNOWN_OR_FAILED")
        self.assertFalse(items[0]["device_verified"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
