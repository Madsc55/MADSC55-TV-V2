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
    def test_real_59_workflows_are_protected_as_one_group(self):
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        result = audit_repository(root, minimum_workflows=59)
        self.assertEqual(result["status"], "DEVELOPMENT_BRANCH_TRIGGER_GATE_PASS",
                         result["issues"])
        self.assertEqual(result["workflows_checked"], 59)
        self.assertEqual(result["locked_publishers"], len(LOCKED_PUBLISHERS))
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["default_branch_runtime_schedules_disabled"],
                         "NOT_VERIFIABLE_FROM_DEV_BRANCH")

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
