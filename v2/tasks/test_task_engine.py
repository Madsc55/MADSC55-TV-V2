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

    def test_all_33_complete_and_dependency_graph(self):
        tasks, rows = e.validate(self.master, self.ledger, self.root)
        self.assertEqual(len(tasks), 33)
        self.assertEqual(len(rows), 33)
        self.assertEqual([t["priority"] for t in self.master["tasks"][:6]], ["P0"] * 6)

    def test_next_and_resume(self):
        self.assertEqual(e.select(self.master, self.ledger, self.root), 1)
        ledger = copy.deepcopy(self.ledger)
        ledger["statuses"][0]["status"] = "blocked"
        self.assertEqual(e.select(self.master, ledger, self.root), 4)

    def test_independent_work_after_p0_completion(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["statuses"][1].update(status="completed",
            evidence_urls=["https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42250095219"],
            last_checked_at="2026-11-06T16:15:00Z")
        self.assertEqual(e.select(self.master, ledger, self.root), 1)
        independent = e.independent_ready(self.master, ledger, self.root, excluded=(1,))
        self.assertNotIn(2, independent)
        self.assertEqual(independent[:5], [4, 7, 8, 9, 10])
        self.assertIn(13, independent)

    def test_completed_not_reselected(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["statuses"][0].update(status="completed", evidence_urls=["https://github.com/example/evidence"], last_checked_at="2026-11-06T16:00:00Z")
        self.assertNotEqual(e.select(self.master, ledger, self.root), 1)
        self.assertEqual(e.select(self.master, ledger, self.root), 4)

    def test_failed_cannot_be_marked_complete(self):
        with self.assertRaisesRegex(ValueError, "No completion"):
            e.safe_transition(self.ledger["statuses"][0], "completed")

    def test_github_offline_or_failure_is_not_success(self):
        for value in (None, {}, {"status": "in_progress"}, {"status": "completed", "conclusion": "failure"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                e.require_fresh_github(value)

    def test_grouped_actions_same_commit_and_all_success(self):
        sha = "a" * 40
        names = ["V2 Master Engine", "V2 Eight-Stage Runner Verification"]
        runs = [{"name": name, "head_sha": sha, "status": "completed",
                 "conclusion": "success", "id": i + 100,
                 "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/" + str(i + 100)}
                for i, name in enumerate(names)]
        self.assertEqual(len(e.verify_grouped_actions(runs, sha, names)), 2)
        for changed in (
            lambda r: r[0].update(status="in_progress", conclusion=None),
            lambda r: r[0].update(conclusion="failure"),
            lambda r: r[0].update(head_sha="b" * 40),
            lambda r: r.pop(),
            lambda r: r[0].update(html_url="https://invalid.example/1"),
        ):
            broken = copy.deepcopy(runs)
            changed(broken)
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                e.verify_grouped_actions(broken, sha, names)

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

    def test_device_test_user_only(self):
        with self.assertRaisesRegex(ValueError, "Only user"):
            e.safe_transition(self.ledger["statuses"][31], "completed",
                              ["https://github.com/example/evidence"], "2026-11-06T16:00:00Z")

    def test_dependency_cycle_rejected(self):
        master = copy.deepcopy(self.master)
        master["tasks"][0]["depends_on"] = [3]
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            e.validate(master, self.ledger, self.root)

    def test_root_link_required(self):
        root = copy.deepcopy(self.root)
        root.pop("task_tracking", None)
        with self.assertRaisesRegex(ValueError, "Canonical"):
            e.validate(self.master, self.ledger, root)


if __name__ == "__main__":
    unittest.main()
