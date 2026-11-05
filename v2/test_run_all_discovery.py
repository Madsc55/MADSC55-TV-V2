#!/usr/bin/env python3
"""No-network tests for the ordered, single-command discovery coordinator."""
import pathlib
import json
import tempfile
import unittest
from unittest.mock import patch
from run_all_discovery import plan, preflight, execute, validate_source_inventory

class RunnerTests(unittest.TestCase):
    def test_source_inventory_preflight_rejects_bad_entries_together(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "sources.json"
            valid = {"id": "tr", "kind": "m3u", "url": "https://example.org/tr.m3u", "scope": "TR"}
            cases = [
                [valid, dict(valid, id="duplicate")],
                [dict(valid, url="http://example.org/tr.m3u")],
                [dict(valid, url="https://user:pass@example.org/tr.m3u")],
                [dict(valid, scope="unsupported")],
                [],
            ]
            for sources in cases:
                with self.subTest(sources=sources):
                    path.write_text(json.dumps({"policy": "discovery-only; never modify live playlist", "sources": sources}), encoding="utf-8")
                    with self.assertRaises(RuntimeError):
                        validate_source_inventory(path)

    def test_real_config_inventory_validates_offline(self):
        self.assertGreater(validate_source_inventory(), 0)

    def test_stage_order(self):
        steps = plan(pathlib.Path("/tmp/private.enc"), pathlib.Path("/tmp/old.json"))
        expected = [
            "source_availability_audit.py", "github_source_discovery.py",
            "run_forge_source_discovery.py", "official_sites_discovery.py",
            "official_site_gap.py", "run_live_page_discovery.py",
            "run_webpage_playlist_discovery.py", "document_platform_discovery.py",
            "traz_api_source_batch.py", "youtube_discovery.py", "discover.py", "source_integration_gate.py"
        ]
        self.assertEqual(len(steps), 12)
        self.assertEqual([pathlib.Path(cmd[1]).name for cmd in steps], expected)
        self.assertIn("--include-original-run60-github-sources", steps[-2])
        self.assertIn("--include-reviewed-public-source-references", steps[-2])
        self.assertIn("--include-approved-live-page-indexes", steps[-2])
        self.assertIn("--encrypted-archive", steps[-2])
        self.assertIn("--accept-partial-routing", steps[-1])
        self.assertEqual(steps[-2][-2:], ["--previous-report", "/tmp/old.json"])

    def test_source_only_runs_all_configured_adapters_without_archive(self):
        steps=plan(source_only=True)
        names=[pathlib.Path(cmd[1]).name for cmd in steps]
        self.assertEqual(len(names),12)
        self.assertEqual(names[-3:],
                         ["youtube_discovery.py","discover.py","source_integration_gate.py"])
        self.assertNotIn("--encrypted-archive",steps[-2])
        self.assertIn("--accept-partial-routing",steps[-1])
        self.assertIn("--public-only", steps[-4])
        self.assertIn("--include-original-run60-github-sources",steps[-2])
        self.assertIn("--include-reviewed-public-source-references",steps[-2])
        self.assertIn("--include-approved-live-page-indexes",steps[-2])
        with self.assertRaises(ValueError):
            plan(pathlib.Path("/tmp/not-allowed.enc"),source_only=True)
        with self.assertRaises(ValueError):
            plan()

    def test_source_only_checks_protected_hashes_without_cryptographic_bypass(self):
        from run_all_discovery import check_immutable_read_only_baseline
        check_immutable_read_only_baseline()
        with (patch("run_all_discovery.check",
                    side_effect=RuntimeError("Must not inspect remote archive")),
              patch("run_all_discovery._cipher",
                    side_effect=RuntimeError("Must not need key")),
              patch("run_all_discovery.shutil.which",return_value="yt-dlp")):
            self.assertTrue(preflight(source_only=True))
        with self.assertRaisesRegex(RuntimeError,"must not touch"):
            preflight(pathlib.Path("/tmp/archive.enc"),source_only=True)

    def test_source_only_detects_protected_baseline_mismatch(self):
        from run_all_discovery import check_immutable_read_only_baseline
        with tempfile.TemporaryDirectory() as tmp:
            fake_root=pathlib.Path(tmp)/"v2"
            fake_root.mkdir()
            (pathlib.Path(tmp)/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8").write_text("#EXTM3U\\n")
            (fake_root/"history").mkdir()
            (fake_root/"history"/"stage3-4955-hash-only.jsonl").write_text("{}\\n")
            with patch("run_all_discovery.ROOT",fake_root):
                with self.assertRaisesRegex(RuntimeError,"baseline mismatch"):
                    check_immutable_read_only_baseline()

    def test_youtube_opt_out_keeps_official_and_final_gate(self):
        steps = plan(pathlib.Path("/tmp/private.enc"), include_youtube=False)
        names = [pathlib.Path(x[1]).name for x in steps]
        self.assertEqual(len(names), 11)
        self.assertNotIn("youtube_discovery.py", names)
        self.assertEqual(names[-2:], ["discover.py", "source_integration_gate.py"])
        self.assertIn("official_site_gap.py", names)

    def test_refuse_without_archive_approval_before_network(self):
        with patch("run_all_discovery.check", side_effect=RuntimeError("no restore evidence")):
            with self.assertRaisesRegex(RuntimeError, "no restore evidence"):
                preflight(pathlib.Path("/tmp/v2-test-archive.enc"))
    def test_preflight_rejects_directory_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("run_all_discovery.check", return_value=True), patch("run_all_discovery._cipher", return_value=object()):
                with self.assertRaisesRegex(RuntimeError, "regular file"):
                    preflight(pathlib.Path(folder))
    def test_stop_after_failure(self):
        calls = []
        class Result:
            def __init__(self, code): self.returncode = code
        def fake(command, **kwargs):
            calls.append(command)
            return Result(1 if len(calls) == 2 else 0)
        with self.assertRaisesRegex(RuntimeError, "stage 2"):
            execute([["first"], ["second"], ["third"]], fake)
        self.assertEqual(len(calls), 2)
    def test_availability_failure_stops_before_discovery(self):
        calls = []
        class Result:
            def __init__(self, code): self.returncode = code
        def fake(command, **kwargs):
            calls.append(command)
            return Result(1 if len(calls) == 1 else 0)
        with self.assertRaisesRegex(RuntimeError, "stage 1"):
            execute([["availability"], ["github"], ["encrypted"]], fake)
        self.assertEqual(len(calls), 1)
    def test_success_runs_all_steps(self):
        class Result:
            returncode = 0
        calls = []
        def fake(command, **kwargs):
            calls.append(command)
            return Result()
        self.assertTrue(execute([["a"], ["b"], ["c"]], fake))
        self.assertEqual(len(calls), 3)
if __name__ == "__main__":
    unittest.main(verbosity=2)
