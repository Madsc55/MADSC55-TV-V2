"""Offline regression tests: no network, no playlist writes."""
import copy
import json
from pathlib import Path
import unittest
import task_engine as e

ROOT = Path(__file__).resolve().parents[2]


class TaskEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master = json.loads((ROOT / "v2/tasks/master_tasks.json").read_text())
        cls.ledger = json.loads((ROOT / "v2/tasks/state.json").read_text())
        cls.root = json.loads((ROOT / "state.json").read_text())

    def scenario_ledger(self):
        """Synthetic baseline: tests must not depend on live task completion."""
        ledger = copy.deepcopy(self.ledger)
        ledger["statuses"][0]["status"] = "in_progress"
        ledger["statuses"][11]["status"] = "pending"  # #12 depends on #1
        ledger["statuses"][1]["status"] = "completed"
        ledger["statuses"][3]["status"] = "pending"
        # Preserve original baseline for deterministic historical ordering assertions.
        for task_id in (7, 8, 10, 13):
            ledger["statuses"][task_id - 1]["status"] = "pending"
        return ledger

    def test_deferred_scope_is_rejected(self):
        manifest = copy.deepcopy(self.master)
        manifest["tasks"][2]["scope"] = "deferred_optional"
        with self.assertRaisesRegex(ValueError, "mandatory"):
            e.validate(manifest, self.ledger, self.root)

    def test_all_34_registered_and_dependency_graph(self):
        tasks, rows = e.validate(self.master, self.ledger, self.root)
        self.assertEqual(len(tasks), 34)
        self.assertEqual(len(rows), 34)
        self.assertEqual([t["priority"] for t in self.master["tasks"][:6]], ["P0"] * 6)

    def test_completed_task_requires_completed_dependencies(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["statuses"][0]["status"] = "in_progress"
        with self.assertRaisesRegex(ValueError, "unfinished dependencies"):
            e.validate(self.master, ledger, self.root)
        ledger = copy.deepcopy(self.ledger)
        ledger["statuses"][1]["status"] = "pending"  # #7, #8, #10, #22, #27 depend on #2
        with self.assertRaisesRegex(ValueError, "unfinished dependencies"):
            e.validate(self.master, ledger, self.root)

    def test_next_and_resume(self):
        ledger = self.scenario_ledger()
        self.assertEqual(e.select(self.master, ledger, self.root), 1)
        ledger["statuses"][0]["status"] = "blocked"
        self.assertIn(e.select(self.master, ledger, self.root), (3, 4, 5, 9))

    def test_independent_work_after_p0_completion(self):
        ledger = self.scenario_ledger()
        ledger["statuses"][1].update(status="completed",
            evidence_urls=["https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42250095219"],
            last_checked_at="2026-11-06T16:15:00Z")
        self.assertEqual(e.select(self.master, ledger, self.root), 1)
        independent = e.independent_ready(self.master, ledger, self.root, excluded=(1,))
        self.assertNotIn(2, independent)
        self.assertEqual(independent[:4], [7, 8, 9, 10])
        self.assertIn(13, independent)
        ledger["statuses"][12]["status"] = "blocked"
        independent = e.independent_ready(self.master, ledger, self.root, excluded=(1,))
        self.assertNotIn(13, independent)
        self.assertIn(23, independent)  # An external archive blocker must not stop the motor work.

    def test_all_historical_tasks_remain_mandatory(self):
        ledger = copy.deepcopy(self.ledger)
        # Stable fixture: future closures must not invalidate scheduler tests.
        ledger["statuses"][8]["status"] = "pending"
        ledger["statuses"][4]["status"] = "pending"  # Explicit fixture: live task 5 may be blocked.
        # Task 5 is P0 and ready once tasks 7 and 8 are complete.
        self.assertEqual(e.select(self.master, ledger, self.root, defer_heavy=True), 4)
        ready = e.independent_ready(self.master, ledger, self.root, defer_heavy=True)
        self.assertNotIn(3, ready)  # #1 is unfinished in this fixture.
        self.assertIn(4, ready)
        self.assertIn(9, ready)
        self.assertEqual(ledger["statuses"][2]["status"], "in_progress")
        self.assertEqual(ledger["statuses"][3]["status"], "in_progress")
        # If all other work is blocked, heavy work must remain selectable.
        for row in ledger["statuses"]:
            if row["id"] not in (1, 2, 3, 4, 8, 22):
                row["status"] = "blocked"
        self.assertEqual(e.select(self.master, ledger, self.root, defer_heavy=True), 4)

    def test_cli_includes_all_mandatory_tasks(self):
        import contextlib
        import io
        from unittest.mock import patch
        output = io.StringIO()
        with patch("sys.argv", ["task_engine"]), contextlib.redirect_stdout(output):
            e.main()
        self.assertEqual(json.loads(output.getvalue())["next_task_id"],
                         e.select(self.master, self.ledger, self.root, defer_heavy=True))
        output = io.StringIO()
        with patch("sys.argv", ["task_engine", "--include-heavy"]), contextlib.redirect_stdout(output):
            e.main()
        self.assertEqual(json.loads(output.getvalue())["next_task_id"],
                         e.select(self.master, self.ledger, self.root, defer_heavy=False))

    def test_completed_not_reselected(self):
        ledger = self.scenario_ledger()
        ledger["statuses"][0].update(status="completed", evidence_urls=["https://github.com/example/evidence"], last_checked_at="2026-11-06T16:00:00Z")
        self.assertNotEqual(e.select(self.master, ledger, self.root), 1)
        self.assertEqual(e.select(self.master, ledger, self.root), 4)

    def test_failed_cannot_be_marked_complete(self):
        # Use an unfinished task: repeating an already-completed status is idempotent.
        row = copy.deepcopy(self.ledger["statuses"][12])
        self.assertNotEqual(row["status"], "completed")
        with self.assertRaisesRegex(ValueError, "No completion"):
            e.safe_transition(row, "completed")

    def test_github_offline_or_failure_is_not_success(self):
        for value in (None, {}, {"status": "in_progress"}, {"status": "completed", "conclusion": "failure"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                e.require_fresh_github(value)

    def test_grouped_actions_same_commit_and_all_success(self):
        sha = "a" * 40
        names = ["V2 Master Engine", "V2 Eight-Stage Runner Verification"]
        runs = [{"name": name, "head_sha": sha, "head_branch": e.BRANCH, "event": "push", "status": "completed",
                 "conclusion": "success", "id": i + 100,
                 "jobs_checked": True, "jobs_total_count": 1,
                 "jobs": [{"status": "completed", "conclusion": "success",
                           "steps": [{"conclusion": "success"}]}],
                 "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/" + str(i + 100)}
                for i, name in enumerate(names)]
        self.assertEqual(len(e.verify_grouped_actions(runs, sha, names)), 2)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            e.verify_grouped_actions(runs, sha, [names[0], names[0]])
        with self.assertRaises(ValueError):
            e.verify_grouped_actions(runs, sha, [""])
        with self.assertRaises(ValueError):
            e.verify_grouped_actions(runs, sha, "V2 Master Engine")
        for invalid_sha in ("", "a" * 39, "a" * 41, "g" * 40, "A" * 40):
            with self.subTest(invalid_sha=invalid_sha), self.assertRaises(ValueError):
                e.verify_grouped_actions(runs, invalid_sha, names)
        for changed in (
            lambda r: r[0].update(status="in_progress", conclusion=None),
            lambda r: r[0].update(conclusion="failure"),
            lambda r: r[0].update(head_sha="b" * 40),
            lambda r: r.pop(),
            lambda r: r[0].update(html_url="https://invalid.example/1"),
            lambda r: r[0].update(html_url=r[1]["html_url"]),
            lambda r: r[0].update(id=True),
            lambda r: r[0].update(id=0),
        ):
            broken = copy.deepcopy(runs)
            changed(broken)
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                e.verify_grouped_actions(broken, sha, names)

    def test_grouped_actions_rejects_skipped_or_missing_jobs_and_steps(self):
        sha = "a" * 40
        base = {"name": "V2 Master Engine", "head_sha": sha, "head_branch": e.BRANCH,
                "event": "push", "status": "completed", "conclusion": "success",
                "id": 123, "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123",
                "jobs_checked": True, "jobs_total_count": 1,
                "jobs": [{"status": "completed", "conclusion": "success",
                          "steps": [{"conclusion": "success"}]}]}
        self.assertEqual(len(e.verify_grouped_actions([base], sha, [base["name"]])), 1)
        for change in (
            {"jobs_checked": False}, {"jobs_total_count": 2}, {"jobs": []},
            {"jobs": [{"status": "completed", "conclusion": "skipped",
                       "steps": [{"conclusion": "success"}]}]},
            {"jobs": [{"status": "completed", "conclusion": "success",
                       "steps": [{"conclusion": "skipped"}]}]},
            {"jobs": [{"status": "completed", "conclusion": "success", "steps": []}]},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "job evidence"):
                e.verify_grouped_actions([dict(base, **change)], sha, [base["name"]])

    def test_readonly_root_actions_reconciliation(self):
        sha = "c" * 40
        name = "V2 Master Engine"
        runs = [{"name": name, "head_sha": sha, "head_branch": e.BRANCH, "event": "push", "status": "completed",
                 "conclusion": "success", "id": 1001,
                 "jobs_checked": True, "jobs_total_count": 1,
                 "jobs": [{"status": "completed", "conclusion": "success",
                           "steps": [{"conclusion": "success"}]}],
                 "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/1001"}]
        root = copy.deepcopy(self.root)
        root["last_verified_run_observation"]["development_commit"] = sha
        root_before, ledger_before = copy.deepcopy(root), copy.deepcopy(self.ledger)
        result = e.reconcile_root_actions(root, self.ledger, runs, sha, [name])
        self.assertTrue(result["task_statuses_unchanged"])
        self.assertEqual(root, root_before)
        self.assertEqual(self.ledger, ledger_before)
        for bad in ([], [dict(runs[0], head_sha="d" * 40)],
                    [dict(runs[0], head_branch="main")],
                    [dict(runs[0], event="pull_request")],
                    [dict(runs[0], conclusion="failure")]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                e.reconcile_root_actions(root, self.ledger, bad, sha, [name])
        root = copy.deepcopy(self.root)
        root.pop("last_verified_run_observation", None)
        with self.assertRaises(ValueError):
            e.reconcile_root_actions(root, self.ledger, runs, sha, [name])
        stale = copy.deepcopy(self.root)
        stale["last_verified_run_observation"]["development_commit"] = "d" * 40
        # The root is a historical observation; matching fresh Actions proof wins.
        self.assertEqual(e.reconcile_root_actions(stale, self.ledger, runs, sha, [name])["expected_sha"], sha)
        self.assertEqual(e.reconcile_root_actions(stale, self.ledger, runs, sha, [name])["accepted_runs"][name], runs[0]["html_url"])

    def test_concurrent_state_conflict(self):
        self.assertTrue(e.require_matching_sha("sha1", "sha1"))
        with self.assertRaisesRegex(ValueError, "Concurrent"):
            e.require_matching_sha("sha2", "sha1")

    def test_protected_branch_and_playlist(self):
        for path, branch in (("v2/tasks/state.json", "main"),
                             ("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8", e.BRANCH),
                             ("../state.json", e.BRANCH)):
            with self.subTest(path=path), self.assertRaises(ValueError):
                e.assert_safe_write(path, branch)
        self.assertTrue(e.assert_safe_write("v2/tasks/progress.md", e.BRANCH))
        for unsafe in ("v2/../state.json", "v2/tasks/../../state.json",
                       "/tmp/state.json", "v2//state.json", "./state.json",
                       "v2/./state.json",
                       "v2/tasks/../MADSC55_TV_IBO_CALISANLAR_TEST.m3u8",
                       "", None):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                e.assert_safe_write(unsafe, e.BRANCH)

    def test_completed_task_cannot_silently_regress(self):
        row = copy.deepcopy(self.ledger["statuses"][1])
        self.assertEqual(row["status"], "completed")
        for target in ("pending", "in_progress", "blocked"):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "downgraded"):
                e.safe_transition(row, target)

    def test_device_confirmation_cannot_attach_to_other_tasks(self):
        # Completed and pending tasks must both reject unauthorized device evidence.
        for task_id in (1, 13):
            with self.subTest(task_id=task_id), self.assertRaisesRegex(ValueError, "only applies to task 32"):
                e.safe_transition(self.ledger["statuses"][task_id - 1], "in_progress", user_confirmed=True)

    def test_completed_task_idempotent_without_evidence_replacement(self):
        row = copy.deepcopy(self.ledger["statuses"][0])
        self.assertEqual(e.safe_transition(row, "completed"), row)
        self.assertEqual(e.safe_transition(row, "completed", row["evidence_urls"],
                                           row["last_checked_at"]), row)
        with self.assertRaisesRegex(ValueError, "evidence cannot"):
            e.safe_transition(row, "completed", ["https://example.org/other"])
        with self.assertRaisesRegex(ValueError, "timestamp cannot"):
            e.safe_transition(row, "completed", checked_at="2099-01-01T00:00:00Z")

    def test_completed_task_guard_remains_after_device_validation(self):
        row = copy.deepcopy(self.ledger["statuses"][0])
        with self.assertRaisesRegex(ValueError, "downgraded"):
            e.safe_transition(row, "in_progress", user_confirmed=False)

    def test_device_test_user_only(self):
        with self.assertRaisesRegex(ValueError, "Only user"):
            e.safe_transition(self.ledger["statuses"][31], "completed",
                              ["https://github.com/example/evidence"], "2026-11-06T16:00:00Z")

    def test_issue34_never_starts_before_33_and_explicit_user_approval(self):
        ledger = copy.deepcopy(self.ledger)
        self.assertFalse(e.issue34_ready(self.master, ledger, self.root, user_approved=True))
        for row in ledger["statuses"]:
            row["status"] = "completed"
            row["evidence_urls"] = ["https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"]
            row["last_checked_at"] = "2026-11-08T00:00:00Z"
        # #34 is the next pending task, never a completed prerequisite.
        # Marking it complete would make a later #33=pending fixture corrupt.
        ledger["statuses"][33]["status"] = "pending"
        ledger["statuses"][31]["user_device_confirmation"] = True
        self.assertFalse(e.issue34_ready(self.master, ledger, self.root))
        self.assertFalse(e.issue34_ready(self.master, ledger, self.root, user_approved=1))
        self.assertTrue(e.issue34_ready(self.master, ledger, self.root, user_approved=True))
        for deferred_id in (3, 4, 6):
            ledger["statuses"][deferred_id - 1].update(status="pending", evidence_urls=[], last_checked_at=None)
        self.assertFalse(e.issue34_ready(self.master, ledger, self.root, user_approved=True))
        for task_id in (1, 32, 33):
            broken = copy.deepcopy(ledger)
            broken["statuses"][task_id - 1]["status"] = "pending"
            if task_id in (1, 32):
                # A dependent (#12 or #33) remains completed: reject the corrupt ledger.
                with self.assertRaisesRegex(ValueError, "unfinished dependencies"):
                    e.issue34_ready(self.master, broken, self.root, user_approved=True)
            else:
                self.assertFalse(e.issue34_ready(self.master, broken, self.root, user_approved=True))
        broken = copy.deepcopy(ledger)
        broken["statuses"][31]["evidence_urls"] = []
        with self.assertRaises(ValueError):
            e.issue34_ready(self.master, broken, self.root, user_approved=True)

    def test_dependency_cycle_rejected(self):
        master = copy.deepcopy(self.master)
        master["tasks"][0]["depends_on"] = [3]
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            e.validate(master, self.ledger, self.root)

    def test_canonical_state_reconciliation_rejects_mismatches(self):
        for field, invalid in (("manifest", "v2/tasks/other.json"),
                               ("canonical_root", "other.json"),
                               ("total_tasks", 32),
                               ("status_authority", "unknown")):
            root = copy.deepcopy(self.root)
            root["task_tracking"][field] = invalid
            with self.subTest(field=field), self.assertRaises(ValueError):
                e.validate(self.master, self.ledger, root)
        manifest = copy.deepcopy(self.master)
        manifest["canonical_state"] = "other.json"
        with self.assertRaises(ValueError):
            e.validate(manifest, self.ledger, self.root)
        for field, invalid in (("canonical_state", "other.json"),
                               ("schema", 2),
                               ("allowed_statuses", ["pending", "completed"])):
            ledger = copy.deepcopy(self.ledger)
            ledger[field] = invalid
            with self.subTest(field=field), self.assertRaises(ValueError):
                e.validate(self.master, ledger, self.root)

    def test_root_link_required(self):
        root = copy.deepcopy(self.root)
        root.pop("task_tracking", None)
        with self.assertRaisesRegex(ValueError, "Canonical"):
            e.validate(self.master, self.ledger, root)


if __name__ == "__main__":
    unittest.main()
