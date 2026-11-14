#!/usr/bin/env python3
"""Offline regression: previous successful PARTIAL scans must be resume sources."""
import pathlib
import subprocess
import unittest

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
    def test_reads_newest_completed_run_including_successful_partial(self):
        script = restore_shell()
        self.assertIn("select(.status == \"completed\")", script)
        self.assertNotIn("--status failure", script)
        self.assertIn('--workflow v2-real-iptv-scan.yml --branch main', script)
        self.assertIn("for PREVIOUS_RUN in $PREVIOUS_RUNS", script)
        self.assertIn('RESUME_DIR="/tmp/v2-resume/$PREVIOUS_RUN"', script)
        self.assertIn('gh run download "$PREVIOUS_RUN"', script)
        self.assertIn("ibo-scan-progress.enc", script)
        self.assertIn("bootstrap_pending_checkpoint.py", script)
        self.assertIn("break", script)

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
