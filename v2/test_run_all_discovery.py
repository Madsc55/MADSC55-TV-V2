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
        self.assertEqual(len(steps), 8)
        self.assertIn("source_availability_audit.py", steps[0][1])
        self.assertIn("github_source_discovery.py", steps[1][1])
        self.assertIn("run_forge_source_discovery.py", steps[2][1])
        self.assertIn("run_live_page_discovery.py", steps[3][1])
        self.assertIn("run_webpage_playlist_discovery.py", steps[4][1])
        self.assertIn("document_platform_discovery.py", steps[5][1])
        self.assertIn("youtube_discovery.py", steps[6][1])
        self.assertIn("discover.py", steps[7][1])
        self.assertEqual(steps[7][-2:], ["--previous-report", "/tmp/old.json"])
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
