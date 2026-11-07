#!/usr/bin/env python3
"""Offline regression for Actions run status collection."""
import unittest
from unittest.mock import patch
import actions_monitor

class MonitorTests(unittest.TestCase):
    def test_monitor_targets_active_workflow(self):
        self.assertEqual(set(actions_monitor.WORKFLOWS), {
            "v2-eight-stage-verification.yml", "v2-master-engine.yml",
            "v2-source-integration-batch.yml", "v2-ordered-preflight.yml"})

    def test_run_states_and_failed_steps(self):
        runs = [
            {"id": 10, "run_number": 10, "head_sha": "abc", "status": "completed",
             "conclusion": "failure", "html_url": "https://github.com/example/actions/runs/10"},
            {"id": 11, "run_number": 11, "head_sha": "def", "status": "in_progress",
             "conclusion": None, "html_url": "https://github.com/example/actions/runs/11"},
            {"id": 12, "run_number": 12, "head_sha": "ghi", "status": "completed",
             "conclusion": "success", "html_url": "https://github.com/example/actions/runs/12"},
        ]
        def fake_api(path):
            if "/workflows/v2-eight-stage-verification.yml/runs?" in path:
                return {"workflow_runs": runs}
            if "/workflows/" in path:
                return {"workflow_runs": []}
            if path.endswith("/10/jobs?per_page=100"):
                return {"jobs": [{"id": 5, "name": "offline-tests", "status": "completed",
                    "conclusion": "failure", "steps": [
                        {"number": 1, "name": "Checkout", "conclusion": "success"},
                        {"number": 2, "name": "Tests", "conclusion": "failure"}]}]}
            return {"workflow_runs": runs}
        with patch.object(actions_monitor, "TOKEN", "unit-test-token"), patch.object(actions_monitor, "api", side_effect=fake_api):
            result = actions_monitor.collect()
        self.assertEqual([r["status"] for r in result["runs"]], ["completed", "in_progress", "completed"])
        self.assertEqual(result["runs"][0]["jobs"][0]["failed_steps"][0]["name"], "Tests")
        self.assertEqual(result["runs"][1]["jobs"], [])
        self.assertEqual(result["runs"][2]["conclusion"], "success")
        self.assertTrue(all(row["workflow_file"] == "v2-eight-stage-verification.yml" for row in result["runs"]))

    def test_all_grouped_workflows_are_queried(self):
        observed = []
        def fake_api(path):
            observed.append(path)
            workflow = path.split("/workflows/", 1)[1].split("/runs?", 1)[0]
            return {"workflow_runs": [{"id": len(observed), "head_sha": "a" * 40,
                "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/" + str(len(observed)),
                "status": "completed", "conclusion": "success"}]}
        with patch.object(actions_monitor, "api", side_effect=fake_api):
            result = actions_monitor.collect()
        self.assertEqual(len(observed), len(actions_monitor.WORKFLOWS))
        self.assertEqual({row["workflow_file"] for row in result["runs"]},
                         set(actions_monitor.WORKFLOWS))

    def test_green_wrong_branch_or_event_is_not_acceptance_candidate(self):
        cases = [("main", "push", False),
                 (actions_monitor.BRANCH, "pull_request", False),
                 (actions_monitor.BRANCH, "push", True)]
        for target_branch, event, accepted in cases:
            with self.subTest(branch=target_branch, event=event):
                def fake_api(path):
                    return {"workflow_runs": [{"id": 123, "head_sha": "a" * 40,
                        "head_branch": target_branch, "event": event,
                        "status": "completed", "conclusion": "success",
                        "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"}]}
                with patch.object(actions_monitor, "api", side_effect=fake_api), patch.dict(
                        "os.environ", {"GITHUB_SHA": "a" * 40}):
                    result = actions_monitor.collect()
                self.assertTrue(result["runs"])
                self.assertTrue(all(row["acceptance_candidate"] is accepted
                                    for row in result["runs"]))

    def test_historical_green_sha_cannot_be_current_acceptance(self):
        def fake_api(path):
            return {"workflow_runs": [{"id": 123, "head_sha": "b" * 40,
                "head_branch": actions_monitor.BRANCH, "event": "push",
                "status": "completed", "conclusion": "success",
                "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"}]}
        with patch.dict("os.environ", {"GITHUB_SHA": "a" * 40}), patch.object(
                actions_monitor, "api", side_effect=fake_api):
            result = actions_monitor.collect()
        self.assertTrue(all(not row["same_monitor_sha"] and not row["acceptance_candidate"]
                            for row in result["runs"]))

    def test_missing_run_identity_is_rejected(self):
        with patch.object(actions_monitor, "api", return_value={"workflow_runs": [{"status": "completed", "conclusion": "success"}]}):
            with self.assertRaisesRegex(RuntimeError, "incomplete workflow run identity"):
                actions_monitor.collect()

if __name__ == "__main__":
    unittest.main(verbosity=2)
