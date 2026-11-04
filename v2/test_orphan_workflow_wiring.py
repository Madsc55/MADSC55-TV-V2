#!/usr/bin/env python3
"""Prevent regression to the 63-only orphan rescue with false-green AV status."""
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parent.parent / ".github/workflows/v2-orphan-m3u-recovery.yml"


class OrphanWorkflowWiringTests(unittest.TestCase):
    def test_real_dynamic_sources_are_included_before_orphan_probe(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        for required in (
            "v2/github_source_discovery.py",
            "v2/run_forge_source_discovery.py",
            "v2/document_platform_discovery.py",
            "--include-public-discovery",
            "--include-targeted-code-search",
            "--include-public-registry",
            "--history-revisions 300",
        ):
            with self.subTest(field=required):
                self.assertIn(required, content)
        self.assertLess(content.index("v2/github_source_discovery.py"),
                        content.index("v2/orphan_m3u_recovery.py"))

    def test_read_only_one_off_trigger_and_real_av_fail_closed_gate(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("contents: read", text)
        self.assertIn("madsc/v2-discovery-bulk-20261031", text)
        self.assertIn("github.event.head_commit.message", text)
        self.assertIn("v2/orphan_resolution_gate.py", text)
        self.assertIn("--all-candidates-sealed", text)
        self.assertIn("v2/reports/ci/orphan-50-resolution-anonymous.json", text)
        self.assertIn("if: always()", text)
        self.assertNotIn("schedule:", text)


if __name__ == "__main__":
    unittest.main()
