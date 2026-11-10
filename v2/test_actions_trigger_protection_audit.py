#!/usr/bin/env python3
"""One grouped regression suite for V2 Actions trigger and write barriers."""
from pathlib import Path
import tempfile
import unittest

from actions_trigger_protection_audit import (
    audit_repository, validate_workflow, DEV, LOCKED_PUBLISHERS)


def fixture(events="  workflow_dispatch:\n", perms="  contents: read\n",
            run="          echo safe\n"):
    return ("name: Fixture\non:\n" + events + "permissions:\n" + perms +
            "jobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - name: Run\n        run: |\n" + run)


class ActionsTriggerProtectionTests(unittest.TestCase):
    def test_at_least_60_workflows_are_protected_as_one_group(self):
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        result = audit_repository(root, minimum_workflows=60)
        self.assertEqual(result["status"], "DEVELOPMENT_BRANCH_TRIGGER_GATE_PASS",
                         result["issues"])
        self.assertGreaterEqual(result["workflows_checked"], 60)
        self.assertEqual(result["locked_publishers"], len(LOCKED_PUBLISHERS))
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["default_branch_runtime_schedules_disabled"],
                         "NOT_VERIFIABLE_FROM_DEV_BRANCH")

    def test_live_orphan_recovery_remains_manual_only_after_offline_ci(self):
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        path = root / "v2-orphan-m3u-recovery.yml"
        source = path.read_text(encoding="utf-8")
        issues, info = validate_workflow(path, source)
        self.assertEqual(issues, [], issues)
        self.assertEqual(info["events"], ["workflow_dispatch"])
        self.assertIn("test_orphan_resolution_gate", source)
        self.assertIn("cryptography==44.0.2", source)
        self.assertIn("4b1c3cea4b5107a425abab60f62d41f9f81e05a7", source)

    def test_ordered_preflight_installs_crypto_before_discovery_tests(self):
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        path = root / "v2-ordered-preflight.yml"
        source = path.read_text(encoding="utf-8")
        issues, _ = validate_workflow(path, source)
        self.assertEqual(issues, [], issues)
        discovery = source.split("  discovery-tests:\n", 1)[1].split("  safety:\n", 1)[0]
        install = discovery.index("python -m pip install cryptography==44.0.2")
        first_test = discovery.index("python v2/test_discovery_offline_regressions.py")
        self.assertLess(install, first_test)
        self.assertNotIn("cryptography>=42,<47", discovery)

    def test_ordered_preflight_jobs_have_bounded_timeouts(self):
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        path = root / "v2-ordered-preflight.yml"
        source = path.read_text(encoding="utf-8")
        issues, _ = validate_workflow(path, source)
        self.assertEqual(issues, [], issues)
        for job in ("compile", "protect", "discovery-tests", "safety"):
            import re
            pattern = r"(?m)^  " + re.escape(job) + r":\\n(?:(?!^  [a-zA-Z-]+:).)*?^    timeout-minutes: [0-9]+$"
            self.assertRegex(source, pattern, job)
        for job in ("compile", "protect", "discovery-tests", "safety"):
            import re
            damaged = re.sub(r"(?m)(^  " + re.escape(job) + r":\\n(?:    [^\\n]*\\n)*?)    timeout-minutes: [0-9]+\\n",
                             r"\\1", source, count=1)
            self.assertNotEqual(damaged, source, job)
            rejected, _ = validate_workflow(path, damaged)
            self.assertIn("UNBOUNDED_PREFLIGHT_JOB:" + job, rejected)

    def test_playlist_invariant_changes_trigger_grouped_safety_ci(self):
        import yaml
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        workflow = yaml.safe_load(
            (root / "v2-actions-trigger-protection.yml").read_text(encoding="utf-8"))
        event = workflow.get("on", workflow.get(True))
        paths = event["push"]["paths"]
        self.assertIn("v2/test_playlist_invariants.py", paths)
        self.assertIn(".github/workflows/**", paths)

    def test_push_safety_workflow_cannot_launch_live_scan_jobs(self):
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        source = (root / "v2-actions-trigger-protection.yml").read_text(encoding="utf-8")
        import yaml
        jobs = yaml.safe_load(source)["jobs"]
        for name in ("final-worldwide-acceptance", "document-platform-live-audit",
                     "orphan-46-live-recovery"):
            self.assertEqual(jobs[name].get("if"), "${{ false }}", name)

    def test_unknown_automatic_push_is_rejected(self):
        text = fixture("  push:\n    branches: [" + DEV + "]\n")
        issues, _ = validate_workflow(Path("unreviewed-discovery.yml"), text)
        self.assertIn("UNAPPROVED_AUTOMATIC_PUSH", issues)

    def test_unscoped_push_on_allowlisted_test_rejected(self):
        text = fixture("  push:\n    paths: ['v2/**']\n")
        issues, _ = validate_workflow(Path("v2-actions-monitor.yml"), text)
        self.assertIn("PUSH_MUST_BE_SCOPED_TO_DEV", issues)

    def test_schedule_discovery_rejected(self):
        text = fixture("  schedule:\n    - cron: '0 0 * * *'\n")
        issues, _ = validate_workflow(Path("v2-world-discovery.yml"), text)
        self.assertIn("UNAPPROVED_EVENT:schedule", issues)

    def test_contents_write_and_git_push_always_rejected(self):
        text = fixture(perms="  contents: write\n",
                       run="          git push origin HEAD:main\n")
        issues, _ = validate_workflow(Path("v2-epg.yml"), text)
        self.assertIn("CONTENTS_MUST_BE_READ_ONLY", issues)
        self.assertIn("GIT_REPOSITORY_MUTATION_COMMAND", issues)

    def test_job_level_permission_escalation_rejected(self):
        text = fixture().replace("    runs-on:", "    permissions:\n      contents: write\n    runs-on:")
        issues, _ = validate_workflow(Path("v2-epg.yml"), text)
        self.assertIn("UNEXPECTED_JOB_WRITE_PERMISSION:contents", issues)

    def test_persisted_explicit_credentials_rejected(self):
        text = fixture().replace("      - name: Run", "      - uses: actions/checkout@v4\n"
                                "        with:\n          persist-credentials: true\n"
                                "      - name: Run")
        issues, _ = validate_workflow(Path("v2-epg.yml"), text)
        self.assertIn("PERSISTED_WRITE_CREDENTIALS", issues)

    def test_mutating_legacy_workflow_requires_lock_job(self):
        text = fixture()
        issues, _ = validate_workflow(Path("alphabetize-yeni-turk.yml"), text)
        self.assertIn("LEGACY_PUBLISHER_MISSING_READONLY_LOCK", issues)
        self.assertIn("LEGACY_PUBLISHER_MISSING_PLAYLIST_HASH", issues)

    def test_unknown_workflow_run_or_target_event_rejected(self):
        for event in ("workflow_run", "pull_request_target", "repository_dispatch"):
            text = fixture("  " + event + ":\n")
            issues, _ = validate_workflow(Path("injected.yml"), text)
            self.assertIn("UNAPPROVED_EVENT:" + event, issues)

    def test_missing_files_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "one.yml").write_text(fixture())
            result = audit_repository(p)
            self.assertIn("WORKFLOW_INVENTORY_INCOMPLETE", result["issues"])
            self.assertEqual(result["status"], "DEVELOPMENT_BRANCH_TRIGGER_GATE_FAIL")


if __name__ == "__main__":
    unittest.main()
