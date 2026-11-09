#!/usr/bin/env python3
"""Offline regression for Actions run status collection."""
import unittest
import io
from contextlib import redirect_stdout
from datetime import datetime, timezone, timedelta
import urllib.error
from unittest.mock import patch
import actions_monitor

class MonitorTests(unittest.TestCase):
    def test_main_emits_stalled_warning_without_retry(self):
        result = {"runs": [{"id": 17, "workflow_file": "v2-source-integration-batch.yml",
            "possibly_stalled": True, "head_sha": "a" * 40, "status": "in_progress",
            "conclusion": None, "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/17"}]}
        output = io.StringIO()
        with patch.object(actions_monitor, "collect", return_value=result), patch.object(
                actions_monitor.Path, "write_text", return_value=None), redirect_stdout(output):
            actions_monitor.main()
        self.assertIn("::warning::Potentially stalled Actions run 17", output.getvalue())
        self.assertIn("no automatic retry", output.getvalue())

    def test_stalled_run_age_is_advisory_and_never_retries(self):
        now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
        old = (now - timedelta(hours=3)).isoformat()
        fresh = (now - timedelta(minutes=10)).isoformat()
        self.assertTrue(actions_monitor.stalled_run(
            {"status": "in_progress", "created_at": old}, now=now))
        self.assertFalse(actions_monitor.stalled_run(
            {"status": "queued", "created_at": fresh}, now=now))
        self.assertFalse(actions_monitor.stalled_run(
            {"status": "completed", "created_at": old}, now=now))
        self.assertIsNone(actions_monitor.stalled_run(
            {"status": "in_progress", "created_at": "invalid"}, now=now))
        self.assertIsNone(actions_monitor.stalled_run(
            {"status": "in_progress", "created_at": "2026-11-09T09:00:00"}, now=now))
        self.assertIsNone(actions_monitor.stalled_run(
            {"status": "in_progress"}, now=now))
        self.assertIsNone(actions_monitor.stalled_run(
            {"status": "in_progress", "created_at": (now + timedelta(hours=1)).isoformat()}, now=now))

    def test_source_integration_stall_budget_is_longer_than_standard(self):
        now = datetime(2026, 11, 9, 18, 0, tzinfo=timezone.utc)
        started = (now - timedelta(hours=4)).isoformat()
        run = {"status": "in_progress", "created_at": started}
        self.assertTrue(actions_monitor.stalled_run(
            run, now=now, threshold_seconds=2 * 3600))
        self.assertFalse(actions_monitor.stalled_run(
            run, now=now, threshold_seconds=6 * 3600))
        self.assertTrue(actions_monitor.stalled_run(
            run, now=now, threshold_seconds=3 * 3600))

    def test_transient_api_failure_retries_then_succeeds(self):
        payload = io.BytesIO(b'{"workflow_runs": []}')
        class Response:
            def __enter__(self):
                return payload
            def __exit__(self, *args):
                return False
        transient = urllib.error.HTTPError("https://api.github.com", 503, "temporary", {}, None)
        with patch.object(actions_monitor, "TOKEN", "test"), patch.object(
                actions_monitor.urllib.request, "urlopen", side_effect=[transient, Response()]) as opener, patch.object(
                actions_monitor.time, "sleep") as sleep:
            self.assertEqual(actions_monitor.api("/test"), {"workflow_runs": []})
        self.assertEqual(opener.call_count, 2)
        sleep.assert_called_once()

    def test_authorization_failure_never_retries(self):
        denied = urllib.error.HTTPError("https://api.github.com", 403, "forbidden", {}, None)
        with patch.object(actions_monitor, "TOKEN", "test"), patch.object(
                actions_monitor.urllib.request, "urlopen", side_effect=denied) as opener, patch.object(
                actions_monitor.time, "sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                actions_monitor.api("/test")
        self.assertEqual(opener.call_count, 1)
        sleep.assert_not_called()

    def test_monitor_targets_active_workflow(self):
        self.assertEqual(set(actions_monitor.WORKFLOWS), {
            "v2-eight-stage-verification.yml", "v2-master-engine.yml",
            "v2-source-integration-batch.yml", "v2-ordered-preflight.yml"})

    def test_run_states_and_failed_steps(self):
        runs = [
            {"id": 10, "run_number": 10, "head_sha": "a" * 40, "status": "completed",
             "conclusion": "failure", "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/10"},
            {"id": 11, "run_number": 11, "head_sha": "b" * 40, "status": "in_progress",
             "conclusion": None, "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/11"},
            {"id": 12, "run_number": 12, "head_sha": "c" * 40, "status": "completed",
             "conclusion": "success", "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/12"},
        ]
        def fake_api(path):
            if "/workflows/v2-eight-stage-verification.yml/runs?" in path:
                return {"workflow_runs": runs}
            if "/workflows/" in path:
                return {"workflow_runs": []}
            if path.endswith("/10/jobs?per_page=100"):
                return {"total_count": 1, "jobs": [{"id": 5, "name": "offline-tests", "status": "completed",
                    "conclusion": "failure", "steps": [
                        {"number": 1, "name": "Checkout", "conclusion": "success"},
                        {"number": 2, "name": "Tests", "conclusion": "failure"}]}]}
            if path.endswith("/12/jobs?per_page=100"):
                return {"total_count": 1, "jobs": [{"id": 6, "name": "offline-tests", "status": "completed", "conclusion": "success", "steps": [{"number": 1, "name": "Checks", "conclusion": "success"}]}]}
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
            if "/runs/" in path and path.endswith("/jobs?per_page=100"):
                return {"total_count": 1, "jobs": [{"id": 90, "status": "completed", "conclusion": "success", "steps": [{"number": 1, "name": "Checks", "conclusion": "success"}]}]}
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
                    if path.endswith("/123/jobs?per_page=100"):
                        return {"total_count": 1, "jobs": [{"id": 124, "status": "completed", "conclusion": "success", "steps": [{"number": 1, "name": "Checks", "conclusion": "success"}]}]}
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
            if path.endswith("/123/jobs?per_page=100"):
                return {"total_count": 1, "jobs": [{"id": 124, "status": "completed", "conclusion": "success", "steps": [{"number": 1, "name": "Checks", "conclusion": "success"}]}]}
            return {"workflow_runs": [{"id": 123, "head_sha": "b" * 40,
                "head_branch": actions_monitor.BRANCH, "event": "push",
                "status": "completed", "conclusion": "success",
                "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"}]}
        with patch.dict("os.environ", {"GITHUB_SHA": "a" * 40}), patch.object(
                actions_monitor, "api", side_effect=fake_api):
            result = actions_monitor.collect()
        self.assertTrue(all(not row["same_monitor_sha"] and not row["acceptance_candidate"]
                            for row in result["runs"]))

    def test_skipped_or_missing_jobs_never_promote_green_workflow(self):
        for jobs, total in (([], 0),
                            ([{"id": 7, "status": "completed", "conclusion": "skipped"}], 1),
                            ([{"id": 7, "status": "completed", "conclusion": "success"}], 2)):
            with self.subTest(jobs=jobs, total=total):
                def fake_api(path):
                    if path.endswith("/123/jobs?per_page=100"):
                        return {"total_count": total, "jobs": jobs}
                    return {"workflow_runs": [{"id": 123, "head_sha": "a" * 40,
                        "head_branch": actions_monitor.BRANCH, "event": "push",
                        "status": "completed", "conclusion": "success",
                        "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"}]}
                with patch.dict("os.environ", {"GITHUB_SHA": "a" * 40}), patch.object(
                        actions_monitor, "api", side_effect=fake_api):
                    if not jobs or total != len(jobs):
                        with self.assertRaisesRegex(RuntimeError, "Incomplete Actions job details"):
                            actions_monitor.collect()
                    else:
                        result = actions_monitor.collect()
                        self.assertTrue(all(not row["acceptance_candidate"] for row in result["runs"]))

    def test_green_job_with_failed_skipped_or_missing_step_is_not_accepted(self):
        for steps in (
            [{"number": 1, "name": "Offline", "conclusion": "failure"}],
            [{"number": 1, "name": "AV", "conclusion": "skipped"}],
            [{"number": 1, "name": "Archive", "conclusion": "cancelled"}],
            [{"number": 1, "name": "Checks", "conclusion": None}],
            [],
            None,
        ):
            with self.subTest(steps=steps):
                job = {"id": 124, "status": "completed", "conclusion": "success"}
                if steps is not None:
                    job["steps"] = steps
                def fake_api(path):
                    if path.endswith("/123/jobs?per_page=100"):
                        return {"total_count": 1, "jobs": [job]}
                    return {"workflow_runs": [{"id": 123, "head_sha": "a" * 40,
                        "head_branch": actions_monitor.BRANCH, "event": "push",
                        "status": "completed", "conclusion": "success",
                        "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"}]}
                with patch.dict("os.environ", {"GITHUB_SHA": "a" * 40}), patch.object(
                        actions_monitor, "api", side_effect=fake_api):
                    result = actions_monitor.collect()
                self.assertTrue(all(not row["acceptance_candidate"] for row in result["runs"]))

    def test_failure_reasons_cover_failed_jobs_skipped_steps_and_stale_sha(self):
        scenarios = [
            ("failure", "failure", [{"number": 1, "name": "AV", "conclusion": "failure"}],
             "job_124_step_1_failure"),
            ("success", "success", [{"number": 2, "name": "Archive", "conclusion": "skipped"}],
             "job_124_step_2_skipped"),
            ("success", "success", [{"number": 3, "name": "Checks", "conclusion": "success"}],
             "not_current_commit_or_incomplete_step_evidence"),
        ]
        for workflow_conclusion, job_conclusion, steps, expected in scenarios:
            with self.subTest(expected=expected):
                def fake_api(path):
                    if path.endswith("/123/jobs?per_page=100"):
                        return {"total_count": 1, "jobs": [{"id": 124,
                            "status": "completed", "conclusion": job_conclusion, "steps": steps}]}
                    return {"workflow_runs": [{"id": 123, "head_sha": "b" * 40,
                        "head_branch": actions_monitor.BRANCH, "event": "push",
                        "status": "completed", "conclusion": workflow_conclusion,
                        "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"}]}
                with patch.dict("os.environ", {"GITHUB_SHA": "a" * 40}), patch.object(
                        actions_monitor, "api", side_effect=fake_api):
                    result = actions_monitor.collect()
                self.assertTrue(result["runs"])
                self.assertIn(expected, result["runs"][0]["failure_reasons"])
                self.assertFalse(result["runs"][0]["acceptance_candidate"])

    def test_untrusted_run_identity_and_truncated_job_pages_rejected(self):
        base = {"id": 123, "head_sha": "a" * 40, "head_branch": actions_monitor.BRANCH,
                "event": "push", "status": "completed", "conclusion": "success",
                "html_url": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"}
        for changed in ({"id": True}, {"id": -1}, {"head_sha": "a" * 39},
                        {"head_sha": "G" * 40}, {"html_url": "https://example.com/123"}):
            with self.subTest(changed=changed):
                def fake_api(path):
                    return {"workflow_runs": [dict(base, **changed)]}
                with patch.object(actions_monitor, "api", side_effect=fake_api):
                    with self.assertRaisesRegex(RuntimeError, "untrusted"):
                        actions_monitor.collect()
        for total in (0, 2, None, True):
            with self.subTest(total=total):
                def fake_api(path):
                    if path.endswith("/123/jobs?per_page=100"):
                        return {"total_count": total, "jobs": [{"id": 12, "status": "completed",
                            "conclusion": "success", "steps": [{"number": 1, "conclusion": "success"}]}]}
                    return {"workflow_runs": [base]}
                with patch.object(actions_monitor, "api", side_effect=fake_api):
                    with self.assertRaisesRegex(RuntimeError, "Incomplete Actions job details"):
                        actions_monitor.collect()

    def test_missing_run_identity_is_rejected(self):
        with patch.object(actions_monitor, "api", return_value={"workflow_runs": [{"status": "completed", "conclusion": "success"}]}):
            with self.assertRaisesRegex(RuntimeError, "incomplete or untrusted workflow run identity"):
                actions_monitor.collect()

if __name__ == "__main__":
    unittest.main(verbosity=2)
