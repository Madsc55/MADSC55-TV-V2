#!/usr/bin/env python3
"""Grouped no-network tests for GitHub main safety lock."""
import unittest
from main_actions_security_gate import audit_one,GATE,WORKFLOWS,WRITER_SUSPENDED

def fixture(events="  workflow_dispatch:\n", perms="  contents: read\n",
            job="    runs-on: ubuntu-latest\n    steps:\n      - run: echo safe\n"):
    return "name: test\non:\n"+events+"permissions:\n"+perms+"jobs:\n  verify:\n"+job

class MainActionsGateTests(unittest.TestCase):
    def test_manual_readonly_allowed(self):
        self.assertEqual(audit_one("v2-world-discovery.yml",fixture()),[])
    def test_cron_rejected(self):
        text=fixture("  workflow_dispatch:\n  schedule:\n    - cron: '0 2 * * *'\n")
        self.assertIn("UNAPPROVED_TRIGGER",audit_one("v2-world-discovery.yml",text))
    def test_push_rejected(self):
        text=fixture("  workflow_dispatch:\n  push:\n    branches: [main]\n")
        self.assertIn("UNAPPROVED_TRIGGER",audit_one("v2-world-discovery.yml",text))
    def test_contents_write_rejected(self):
        self.assertIn("WORKFLOW_HAS_WRITE_PERMISSION",
                      audit_one("v2-world-discovery.yml",fixture(perms="  contents: write\n")))
    def test_job_write_rejected(self):
        job="    runs-on: ubuntu-latest\n    permissions:\n      contents: write\n    steps:\n      - run: echo safe\n"
        self.assertIn("JOB_HAS_WRITE_PERMISSION",audit_one("v2-world-discovery.yml",fixture(job=job)))
    def test_persisted_checkout_rejected(self):
        job="    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          persist-credentials: true\n"
        self.assertIn("PERSISTED_CHECKOUT_WRITE_CREDENTIALS",
                      audit_one("v2-world-discovery.yml",fixture(job=job)))
    def test_manual_git_push_rejected(self):
        job="    runs-on: ubuntu-latest\n    steps:\n      - run: git push origin HEAD:main\n"
        self.assertIn("GIT_MUTATION_COMMAND",audit_one("v2-world-discovery.yml",fixture(job=job)))
    def test_old_writer_still_requires_suspension(self):
        self.assertIn("ORIGINAL_PRODUCTION_WRITER_REENABLED",
                      audit_one(sorted(WRITER_SUSPENDED)[0],fixture()))
    def test_main_gate_rejects_wrong_push_scope(self):
        text=fixture("  workflow_dispatch:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n")
        self.assertIn("MAIN_GATE_WRONG_PUSH_BRANCHES",audit_one(GATE,text))
    def test_invalid_yaml_rejected(self):
        self.assertIn("UNPARSEABLE_YAML",audit_one("v2-world-discovery.yml","on: [bad"))
    def test_drive_oidc_requires_the_isolated_push_and_preflight(self):
        text = (WORKFLOWS / GATE).read_text(encoding="utf-8")
        self.assertEqual(audit_one(GATE, text), [])
        for target, replacement in (
            ("github.ref == 'refs/heads/stage4-24-independent-acceptance'", "github.ref == 'refs/heads/main'"),
            ("needs: stage4-drive-preflight", "needs: production-lock"),
            ("id-token: write", "contents: write"),
        ):
            with self.subTest(target=target):
                self.assertIn("JOB_HAS_WRITE_PERMISSION", audit_one(GATE, text.replace(target, replacement, 1)))
if __name__=="__main__":
    unittest.main()
