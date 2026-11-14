#!/usr/bin/env python3
"""Fail-closed regression coverage for the Stage A real-evidence acceptance gate."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stage_a_evidence_review", ROOT / "stage_a_evidence_review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def evidence():
    scan = dict(mock_data_used=False, archive_restore_test_passed=True,
                http_checked=10, unique_new_candidates=10, av_verified=3,
                av_verified_this_run=1, resumed_decoded_av_evidence=2,
                http_checked_this_run=4, resumed_checkpoint_observations=6,
                unverified_or_failed_candidates=7, retried_failed_checkpoint_urls=2,
                recovered_av_from_failed_checkpoint=1, source_count=2,
                fetched_sources=2, status="READY_FOR_DEVICE_TEST",
                configured_sources_complete=True, full_discovery_acceptance=True,
                discovery_partial=False, failed_sources=[], source_drops=[],
                resolved_direct_candidate_count=0)
    epg = dict(verified_exact_id_channels=0, name_hint_channels_not_exact_evidence=2,
               programmes=8, channels=5, candidate_only=True,
               status="EPG_CANDIDATE_FOR_REVIEW")
    integrity = {"status_counts": {"XMLTV_VALID": 1}}
    youtube = dict(videos_checked=4, live_verified=0,
                   verification_failure_categories={"SIGN_IN_REQUIRED": 4},
                   metadata_verification_complete=False)
    gitlab = dict(status="ok", rate_limited=False, queries_checked=2, queries_skipped=0)
    codeberg = dict(status="rate_limited", rate_limited=True,
                    queries_checked=1, queries_skipped=1)
    return scan, epg, integrity, youtube, gitlab, codeberg


class StageAAcceptanceTests(unittest.TestCase):
    def test_real_scan_does_not_close_six_tasks(self):
        result = module.audit(*evidence())
        self.assertFalse(result["final_acceptance"])
        self.assertFalse(result["task_status_changes"])
        self.assertFalse(result["protected_playlists_modified"])
        self.assertEqual(set(result["tasks"]), {"15", "17", "18", "19", "20", "21"})
        self.assertTrue(all(v["status"] == "in_progress" for v in result["tasks"].values()))
        self.assertIn("NO_EXACT_XMLTV_CHANNEL_ID_EVIDENCE", result["tasks"]["19"]["blockers"])
        self.assertIn("RECOVERY_QUEUE_STILL_OPEN", result["tasks"]["17"]["blockers"])
        self.assertIn("GITLAB_CODEBERG_ADAPTERS_INCOMPLETE", result["tasks"]["21"]["blockers"])

    def test_mock_evidence_rejected(self):
        docs = list(evidence())
        docs[0]["mock_data_used"] = True
        with self.assertRaises(module.InvalidEvidence):
            module.audit(*docs)

    def test_corrupt_checkpoint_accounting_rejected(self):
        docs = list(evidence())
        docs[0]["resumed_checkpoint_observations"] = 5
        with self.assertRaises(module.InvalidEvidence):
            module.audit(*docs)

    def test_retry_cannot_exceed_current_probes(self):
        docs = list(evidence())
        docs[0]["retried_failed_checkpoint_urls"] = 5
        with self.assertRaises(module.InvalidEvidence):
            module.audit(*docs)

    def test_epg_name_hints_not_exact_identity(self):
        result = module.audit(*evidence())
        self.assertEqual(result["epg"]["exact_id_channels"], 0)
        self.assertEqual(result["epg"]["name_only_review_channels"], 2)

    def test_boolean_count_rejected(self):
        docs = list(evidence())
        docs[0]["av_verified"] = True
        with self.assertRaises(module.InvalidEvidence):
            module.audit(*docs)


if __name__ == "__main__":
    unittest.main()
