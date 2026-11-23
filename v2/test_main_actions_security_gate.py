#!/usr/bin/env python3
"""Grouped no-network tests for GitHub main safety lock."""
import unittest
import tempfile
from pathlib import Path
from main_actions_security_gate import audit, audit_one,GATE,WRITER_SUSPENDED,preserves_record_multiplicity,safe_favorite_copy,safe_category_reorder

def fixture(events="  workflow_dispatch:\n", perms="  contents: read\n",
            job="    runs-on: ubuntu-latest\n    steps:\n      - run: echo safe\n"):
    return "name: test\non:\n"+events+"permissions:\n"+perms+"jobs:\n  verify:\n"+job

class MainActionsGateTests(unittest.TestCase):
    def test_parts_builder_never_pushes_to_protected_main(self):
        from main_actions_security_gate import ROOT, PARTS_BUILD
        source = (ROOT / ".github/workflows" / PARTS_BUILD).read_text(encoding="utf-8")
        self.assertEqual(audit_one(PARTS_BUILD, source), [])
        unsafe = source.replace('git push origin "HEAD:refs/heads/$branch"',
                                "git push origin HEAD:main")
        self.assertIn("PARTS_BUILD_VALIDATION_OR_WRITE_SCOPE_CHANGED",
                      audit_one(PARTS_BUILD, unsafe))
        untrusted = source.replace("    branches: [main]", "    branches: [main, unsafe]")
        self.assertIn("PARTS_BUILD_UNAPPROVED_TRIGGER",
                      audit_one(PARTS_BUILD, untrusted))

    def test_favorites_copy_preserves_originals_and_rejects_unknown_urls(self):
        source = b'#EXTINF:-1 group-title="YEDEKLER (3)",TRT 1\nhttps://example.test/1\n'
        favorite = b'#EXTINF:-1 group-title="FAVOR\xc4\xb0LER 1 (1)",TRT 1\nhttps://example.test/1\n'
        self.assertTrue(safe_favorite_copy([source], [source, favorite]))
        forged = favorite.replace(b"https://example.test/1", b"https://bad.test/forged")
        self.assertFalse(safe_favorite_copy([source], [source, forged]))
        self.assertFalse(safe_favorite_copy([source], [favorite]))

    def test_category_reorder_counts_are_not_deleted(self):
        one = b'#EXTINF:-1 group-title="HABER (3)",A\nhttps://example.test/a\n'
        two = b'#EXTINF:-1 group-title="HABER (3)",B\nhttps://example.test/b\n'
        one2 = one.replace(b"(3)", b"(2)")
        two2 = two.replace(b"(3)", b"(2)")
        self.assertTrue(safe_category_reorder([one, two], [two2, one2]))
        self.assertFalse(safe_category_reorder([one, two], [two2]))

    def test_manual_readonly_allowed(self):
        self.assertEqual(audit_one("v2-world-discovery.yml",fixture()),[])
    def test_685_manual_publisher_is_scoped(self):
        from main_actions_security_gate import ROOT
        source=(ROOT/".github/workflows/run_move_685.yml").read_text(encoding="utf-8")
        self.assertEqual(audit_one("run_move_685.yml",source),[])
        self.assertIn("685_UNAPPROVED_TRIGGER",
                      audit_one("run_move_685.yml",source.replace(
                          "  workflow_dispatch:", "  workflow_dispatch:\\n  push:\\n    branches: [main]")))
        self.assertIn("685_WRONG_PERMISSIONS",
                      audit_one("run_move_685.yml",source.replace(
                          "  contents: write", "  contents: read")))
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
    def test_playlist_record_multiplicity_guard(self):
        original = [b"duplicate", b"duplicate", b"single"]
        self.assertFalse(preserves_record_multiplicity(original, [b"duplicate", b"single"]))
        self.assertTrue(preserves_record_multiplicity(original, original))
        self.assertTrue(preserves_record_multiplicity(original, original + [b"new"]))
    def test_symlinked_workflow_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / '.github' / 'workflows'
            folder.mkdir(parents=True)
            target = root / 'safe.yml'
            target.write_text(fixture(), encoding='utf-8')
            (folder / 'v2-world-discovery.yml').symlink_to(target)
            report = audit(root)
            self.assertEqual(report['errors']['v2-world-discovery.yml'],
                             ['SYMLINK_WORKFLOW_FORBIDDEN'])

    def test_invalid_yaml_rejected(self):
        self.assertIn("UNPARSEABLE_YAML",audit_one("v2-world-discovery.yml","on: [bad"))
    def test_autonomous_workflow_requires_security_hold(self):
        held = fixture(job="    if: ${{ false }}\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo held\n").replace("  verify:\n", "  acceptance:\n")
        self.assertEqual(audit_one("full_autonomous_pipeline.yml", held), [])
        enabled = held.replace("    if: ${{ false }}", "    if: ${{ true }}")
        self.assertIn("AUTONOMOUS_PIPELINE_SECURITY_HOLD_REQUIRED",
                      audit_one("full_autonomous_pipeline.yml", enabled))
        writer = held.replace("  contents: read", "  contents: write")
        self.assertIn("WORKFLOW_HAS_WRITE_PERMISSION",
                      audit_one("full_autonomous_pipeline.yml", writer))

    def test_685_retry_requires_explicit_security_hold(self):
        held = """name: YEDEKLER uncertain AV retry (SECURITY HOLD)
on:
  workflow_dispatch:
permissions:
  contents: read
  actions: read
jobs:
  retry:
    if: ${{ false }}
    runs-on: ubuntu-latest
    steps:
      - run: echo paused
"""
        self.assertEqual(audit_one("v2-yedekler-av-audit.yml", held), [])
        without_hold = held.replace("    if: ${{ false }}\n", "")
        self.assertIn("UNSAFE_685_LIVE_RETRY_NOT_SUSPENDED",
                      audit_one("v2-yedekler-av-audit.yml", without_hold))
        enabled = held.replace("    if: ${{ false }}", "    if: ${{ true }}")
        self.assertIn("UNSAFE_685_LIVE_RETRY_NOT_SUSPENDED",
                      audit_one("v2-yedekler-av-audit.yml", enabled))
        extra_job = held + """  hidden_network:
    runs-on: ubuntu-latest
    steps:
      - run: echo unsupported
"""
        self.assertIn("UNSAFE_685_LIVE_RETRY_NOT_SUSPENDED",
                      audit_one("v2-yedekler-av-audit.yml", extra_job))
        scheduled = held.replace("  workflow_dispatch:\n",
                                 "  workflow_dispatch:\n  schedule:\n    - cron: '0 2 * * *'\n")
        self.assertIn("UNAPPROVED_TRIGGER",
                      audit_one("v2-yedekler-av-audit.yml", scheduled))

    def test_yedekler_result_reconcile_is_manual_read_only(self):
        source = """name: YEDEKLER existing result reconciliation
on:
  workflow_dispatch:
permissions:
  contents: read
  actions: read
jobs:
  reconcile:
    runs-on: ubuntu-latest
    steps:
      - run: echo preview-only
"""
        self.assertEqual(audit_one("v2-yedekler-result-reconcile.yml", source), [])
        scheduled = """name: YEDEKLER existing result reconciliation
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'
permissions:
  contents: read
  actions: read
jobs:
  reconcile:
    runs-on: ubuntu-latest
    steps:
      - run: echo preview-only
"""
        self.assertIn("UNAPPROVED_TRIGGER",
                      audit_one("v2-yedekler-result-reconcile.yml", scheduled))

if __name__=="__main__":
    unittest.main()
