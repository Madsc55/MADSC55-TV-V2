#!/usr/bin/env python3
"""Offline regression for Actions run status collection."""
import unittest
from unittest.mock import patch
import actions_monitor

class MonitorTests(unittest.TestCase):
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
            if "/workflows/v2-master-engine.yml/runs?" in path:
                return {"workflow_runs": runs}
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

    def test_missing_run_identity_is_rejected(self):
        with patch.object(actions_monitor, "api", return_value={"workflow_runs": [{"status": "completed", "conclusion": "success"}]}):
            with self.assertRaisesRegex(RuntimeError, "incomplete workflow run identity"):
                actions_monitor.collect()

if __name__ == "__main__":
    unittest.main(verbosity=2)
