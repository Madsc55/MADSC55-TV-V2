#!/usr/bin/env python3
"""Deterministic grouped tests for real main/default-branch Actions exposure."""
import unittest
from actions_default_branch_audit import summarize_default_branch

SHA = "a" * 40


def item(name, *, schedule=False, push=False, writer=False, playlist=False):
    ev = "  workflow_dispatch:\n"
    if schedule:
        ev += "  schedule:\n    - cron: '3 4 * * *'\n"
    if push:
        ev += "  push:\n    branches: [main]\n"
    perms = "  contents: write\n" if writer else "  contents: read\n"
    command = ("git add " + ("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8" if playlist
                              else "v2/reports/a.json") +
               "\n          git commit -m 'example' && git push\n") if writer else "echo safe\n"
    return ".github/workflows/" + name + ".yml", (
        "name: Tested\non:\n" + ev + "permissions:\n" + perms +
        "jobs:\n  check:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: |\n          " + command)


class MainDefaultBranchExposureTests(unittest.TestCase):
    def test_unprotected_main_is_never_marked_safe(self):
        a, b = item("safe")
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=False, rulesets=[],
                                           enabled_states={a: "active"})
        self.assertEqual(report["readiness"], "MAIN_DEFAULT_BRANCH_NOT_SAFE")
        self.assertEqual(report["counts"]["scheduled"], 0)
        self.assertEqual(report["branch_protected"], False)

    def test_schedule_and_playlist_writer_are_both_counted(self):
        a, b = item("old-automatic", writer=True, playlist=True, schedule=True, push=True)
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states={a: "active"})
        self.assertEqual(report["readiness"], "MAIN_DEFAULT_BRANCH_NOT_SAFE")
        for key in ("writable_publisher", "scheduled", "push_triggered",
                    "playlist_writer", "enabled_scheduled", "enabled_writable_publisher"):
            self.assertEqual(report["counts"][key], 1, key)
        self.assertEqual(report["workflows"][a]["workflow_state"], "active")

    def test_writer_inline_git_push_not_missed(self):
        a, b = item("inline", writer=True)
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states={a: "disabled_manually"})
        self.assertEqual(report["counts"]["writable_publisher"], 1)
        self.assertEqual(report["counts"]["enabled_writable_publisher"], 0)
        self.assertEqual(report["readiness"], "MAIN_DEFAULT_BRANCH_NOT_SAFE")

    def test_missing_live_state_never_claims_ready(self):
        a, b = item("safe")
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states=None,
                                           source_error="GitHub workflow states unavailable")
        self.assertEqual(report["readiness"],
                         "MAIN_DEFAULT_BRANCH_NOT_FULLY_VERIFIED")

    def test_genuinely_safe_protected_main_requires_live_evidence(self):
        a, b = item("safe")
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states={a: "active"},
                                           pr_policy_verified=True)
        self.assertEqual(report["readiness"], "MAIN_DEFAULT_BRANCH_READY")
        self.assertFalse(report["main_branch_modified"])
        self.assertFalse(report["automations_disabled_by_audit"])

    def test_protected_flag_alone_cannot_certify_required_pr_reviews(self):
        a, b = item("safe")
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states={a: "active"})
        self.assertEqual(report["readiness"],
                         "MAIN_DEFAULT_BRANCH_NOT_FULLY_VERIFIED")
        self.assertFalse(report["required_pr_policy_verified"])

    def test_contents_write_without_git_push_is_not_safe(self):
        a, b = item("api-writer", writer=True)
        b = b.replace("git add v2/reports/a.json", "echo could-use-github-api")
        b = b.replace("git commit -m 'example' && git push", "echo no-git-push")
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states={a: "active"},
                                           pr_policy_verified=True)
        self.assertEqual(report["counts"]["writable_publisher"], 0)
        self.assertEqual(report["counts"]["contents_write_permission"], 1)
        self.assertEqual(report["counts"]["enabled_contents_write_permission"], 1)
        self.assertEqual(report["readiness"], "MAIN_DEFAULT_BRANCH_NOT_SAFE")

    def test_privileged_event_without_push_is_not_safe(self):
        a, b = item("privileged")
        b = b.replace("workflow_dispatch:", "pull_request_target:")
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states={a: "active"},
                                           pr_policy_verified=True)
        self.assertEqual(report["counts"]["privileged_event"], 1)
        self.assertEqual(report["readiness"], "MAIN_DEFAULT_BRANCH_NOT_SAFE")

    def test_git_mutation_without_contents_write_is_detected(self):
        a, b = item("shell")
        b = b.replace("echo safe", "git -C . push origin HEAD:main")
        report = summarize_default_branch({a: b}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states={a: "active"},
                                           pr_policy_verified=True)
        self.assertEqual(report["counts"]["git_mutation_command"], 1)
        self.assertEqual(report["readiness"], "MAIN_DEFAULT_BRANCH_NOT_SAFE")

    def test_malformed_yaml_is_not_trusted(self):
        a, _ = item("bad")
        report = summarize_default_branch({a: "[[ YAML BROKEN"}, revision=SHA,
                                           protection=True, rulesets=[],
                                           enabled_states={a: "active"})
        self.assertEqual(report["counts"]["unparseable"], 1)
        self.assertEqual(report["readiness"], "MAIN_DEFAULT_BRANCH_NOT_SAFE")

    def test_reject_non_immutable_revision(self):
        a, b = item("safe")
        with self.assertRaisesRegex(ValueError, "Non-immutable"):
            summarize_default_branch({a: b}, revision="main")

    def test_missing_snapshot_rejected(self):
        with self.assertRaisesRegex(ValueError, "No default-branch"):
            summarize_default_branch({}, revision=SHA)

    def test_another_repository_cannot_be_injected(self):
        a, b = item("safe")
        with self.assertRaisesRegex(ValueError, "Unexpected workflow pathname"):
            summarize_default_branch({"../../unsafe.yml": b}, revision=SHA)


if __name__ == "__main__":
    unittest.main()
