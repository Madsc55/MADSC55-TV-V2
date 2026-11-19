#!/usr/bin/env python3
"""Offline regression: previous successful PARTIAL scans must be resume sources."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from scan_checkpoint import checkpoint_row, save_progress

WORKFLOW = pathlib.Path(__file__).resolve().parents[1] / ".github/workflows/v2-real-iptv-scan.yml"


def restore_shell():
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index("      - name: Restore authenticated progress")
    tail = text[start:]
    run = tail.index("        run: |\n") + len("        run: |\n")
    after = tail[run:]
    end = after.find("\n      - name:")
    section = after if end == -1 else after[:end]
    return "\n".join(
        line[10:] if line.startswith("          ") else line
        for line in section.splitlines()
    ) + "\n"


class ResumeWorkflowTests(unittest.TestCase):
    def test_worldwide_workflows_check_readiness_before_discovery(self):
        import yaml
        workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        jobs = workflow["jobs"]
        self.assertEqual(jobs["scan"]["needs"], "readiness")
        self.assertEqual(jobs["legacy-verify"]["needs"], "readiness")
        guard = "python v2/prescan_readiness_gate.py"
        self.assertIn(guard, [step.get("run") for step in jobs["readiness"]["steps"]])
        metadata = WORKFLOW.with_name("v2-world-discovery.yml").read_text(encoding="utf-8")
        self.assertLess(metadata.index(guard), metadata.index("python v2/discover.py"))

    def test_export_follows_worldwide_adapter_acceptance(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        gate = "python v2/validate_real_scan_acceptance.py --report v2/reports/ibo-real-scan-report.json --discovery-reports-dir v2/reports"
        self.assertLess(workflow.index(gate), workflow.index("python v2/export_ibo_batches.py"))

    def test_reads_newest_completed_run_including_successful_partial(self):
        script = restore_shell()
        self.assertIn("select(.status == \"completed\")", script)
        self.assertNotIn("--status failure", script)
        self.assertIn('--workflow v2-real-iptv-scan.yml --branch main', script)
        self.assertIn("for PREVIOUS_RUN in $PREVIOUS_RUNS", script)
        self.assertIn('gh run download "$PREVIOUS_RUN"', script)
        self.assertIn("ibo-scan-progress.enc", script)
        self.assertIn("bootstrap_pending_checkpoint.py", script)
        self.assertIn("break", script)

    def test_resume_order_and_encrypted_artifact_integrity(self):
        imported = "44429064188"
        source = "43608247496"
        newer = "43842056360"
        runs = [
            {"databaseId": int(source), "status": "completed", "createdAt": "2026-11-14T15:05:12Z"},
            {"databaseId": 99999999001, "status": "in_progress", "createdAt": "2026-11-20T08:00:00Z"},
            {"databaseId": int(newer), "status": "completed", "createdAt": "2026-11-16T09:41:48Z"},
        ]
        gh_script = """#!/bin/sh
set -eu
case "$2" in
  list) cat "$RUNS" ;;
  download)
    echo "$3 $5" >> "$DOWNLOADS"
    [ "$3" = "$AVAILABLE" ] || exit 1
    cp "$FIXTURE" "$7/ibo-scan-progress.enc" ;;
  *) exit 2 ;;
esac
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            reports = root / "v2/reports"
            reports.mkdir(parents=True)
            module_dir = pathlib.Path(__file__).resolve().parent
            importer = "merge_bounded_retry_checkpoint.py"
            report = "task17-18-20-bounded-retry-20261118.json"
            (root / "v2" / importer).symlink_to(module_dir / importer)
            (reports / report).write_bytes((module_dir / "reports" / report).read_bytes())
            runner_temp = root / "runner"
            runner_temp.mkdir()
            gh = root / "gh"
            gh.write_text(gh_script)
            gh.chmod(0o700)
            fixture = root / "ibo-scan-progress.enc"
            secret = "local-resume-test-passphrase"
            url = "https://example.org/newer-scan"
            save_progress(fixture, secret, worldwide=True,
                          rows={url: checkpoint_row(url, None, {}, checked_at=1)})
            run_list, downloads = root / "runs.json", root / "downloads"
            run_list.write_text(json.dumps(runs))
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"],
                       RUNS=str(run_list), DOWNLOADS=str(downloads), FIXTURE=str(fixture),
                       RUNNER_TEMP=str(runner_temp), V2_ARCHIVE_PASSPHRASE=secret)
            cases = [
                (newer, [newer], True),
                (source, [newer, imported, source], True),
                (imported, [newer, imported], False),  # A different encrypted file at the pinned ID.
            ]
            output = reports / "ibo-scan-resume.enc"
            for available, expected, success in cases:
                with self.subTest(available=available):
                    downloads.write_text("")
                    output.unlink(missing_ok=True)
                    result = subprocess.run(["bash", "-c", restore_shell()], cwd=root,
                                            env={**env, "AVAILABLE": available}, capture_output=True)
                    self.assertEqual(result.returncode == 0, success, result.stderr)
                    entries = [line.split() for line in downloads.read_text().splitlines()]
                    self.assertEqual([run for run, artifact in entries], expected)
                    for run, artifact in entries:
                        expected_name = ("v2-bounded-retry-15-merged-checkpoint" if run == imported
                                         else "v2-real-scan-evidence")
                        self.assertEqual(artifact, expected_name)
                    self.assertEqual(output.exists(), success)
                    if success:
                        self.assertEqual(output.read_bytes(), fixture.read_bytes())

    def test_script_bash_syntax_and_no_writer_permissions(self):
        script = restore_shell()
        result = subprocess.run(
            ["bash", "-n"], input=script, text=True,
            capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("  contents: read", workflow)
        self.assertIn("  actions: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  schedule:", workflow)


if __name__ == "__main__":
    unittest.main()
