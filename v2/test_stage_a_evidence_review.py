#!/usr/bin/env python3
"""Offline, non-network proof that green scanner is not full A-stage acceptance."""
import copy
import unittest
from stage_a_evidence_review import InvalidEvidence, audit


def evidence():
    scan = {
        "mock_data_used": False,
        "archive_restore_test_passed": True,
        "status": "READY_FOR_DEVICE_TEST",
        "configured_sources_complete": True,
        "full_discovery_acceptance": True,
        "discovery_partial": False,
        "source_count": 103, "fetched_sources": 103,
        "failed_sources": [], "source_drops": [],
        "http_checked": 28845, "unique_new_candidates": 28845,
        "av_verified": 8573, "av_verified_this_run": 33,
        "resumed_decoded_av_evidence": 8540,
        "http_checked_this_run": 300,
        "resumed_checkpoint_observations": 28545,
        "unverified_or_failed_candidates": 20272,
        "retried_failed_checkpoint_urls": 300,
        "recovered_av_from_failed_checkpoint": 33,
        "resolved_direct_candidate_count": 0,
    }
    epg = {
        "candidate_only": True, "status": "EPG_CANDIDATE_FOR_REVIEW",
        "channels": 54, "verified_exact_id_channels": 0,
        "name_hint_channels_not_exact_evidence": 54,
        "programmes": 1838,
    }
    epg_audit = {"status_counts": {"XMLTV_VALID": 5}}
    youtube = {
        "videos_checked": 353, "live_verified": 0,
        "verification_failure_categories": {"SIGN_IN_REQUIRED": 353},
        "metadata_verification_complete": False,
    }
    gitlab = {
        "status": "error", "rate_limited": True,
        "queries_checked": 10, "queries_skipped": 2,
    }
    codeberg = {
        "status": "error", "rate_limited": True,
        "queries_checked": 1, "queries_skipped": 11,
    }
    return scan, epg, epg_audit, youtube, gitlab, codeberg


class StageAEvidenceReviewTests(unittest.TestCase):
    def test_actual_green_scan_still_has_six_open_tasks(self):
        result = audit(*evidence())
        self.assertEqual(result["status"], "OPEN_REQUIRES_REAL_WORLD_ACCEPTANCE")
        self.assertFalse(result["final_acceptance"])
        self.assertFalse(result["task_status_changes"])
        self.assertEqual(set(result["tasks"]), {"15", "17", "18", "19", "20", "21"})
        self.assertTrue(all(t["status"] == "in_progress" for t in result["tasks"].values()))
        self.assertEqual(result["scan"]["av_decoded_this_run"], 33)
        self.assertEqual(result["scan"]["av_decoded_previous_checkpoint"], 8540)
        self.assertEqual(result["scan"]["av_recovered_from_previous_failures"], 33)
        self.assertEqual(result["scan"]["candidates_without_decoded_av"], 20272)
        self.assertEqual(result["epg"]["exact_id_channels"], 0)
        self.assertEqual(result["epg"]["name_only_review_channels"], 54)
        self.assertEqual(result["discovery"]["youtube_failure_categories"]["SIGN_IN_REQUIRED"], 353)
        self.assertIn("GITLAB_CODEBERG_ADAPTERS_INCOMPLETE",
                      result["tasks"]["21"]["blockers"])

    def test_bad_av_evidence_must_fail_closed(self):
        originals = evidence()
        for field, value in (
            ("av_verified", 9000),
            ("http_checked_this_run", 301),
            ("av_verified_this_run", True),
            ("recovered_av_from_failed_checkpoint", 301),
            ("retried_failed_checkpoint_urls", 301),
            ("unverified_or_failed_candidates", 100),
            ("mock_data_used", True),
            ("archive_restore_test_passed", False),
        ):
            with self.subTest(field=field):
                altered = copy.deepcopy(originals)
                altered[0][field] = value
                with self.assertRaises(InvalidEvidence):
                    audit(*altered)

    def test_configured_source_failure_is_reported_as_blocker(self):
        data = copy.deepcopy(evidence())
        data[0]["full_discovery_acceptance"] = False
        data[0]["configured_sources_complete"] = False
        data[0]["failed_sources"] = [{"id": "configured"}]
        self.assertFalse(audit(*data)["scan"]["core_configured_sources_complete"])
        self.assertIn("CORE_M3U_SOURCE_COVERAGE_INCOMPLETE",
                      audit(*data)["tasks"]["21"]["blockers"])

    def test_exact_epg_is_not_yet_a_complete_epg_acceptance(self):
        data = copy.deepcopy(evidence())
        data[1]["verified_exact_id_channels"] = 5
        report = audit(*data)
        self.assertIn("EPG_GAPS_AND_PUBLISHER_LINKAGE_NOT_FULLY_CLOSED",
                      report["tasks"]["19"]["blockers"])
        self.assertFalse(report["final_acceptance"])

    def test_no_automatic_publisher_or_device_signoff(self):
        data = copy.deepcopy(evidence())
        data[0]["unverified_or_failed_candidates"] = 0
        data[0]["av_verified"] = data[0]["http_checked"]
        data[0]["av_verified_this_run"] = 300
        data[0]["resumed_decoded_av_evidence"] = data[0]["http_checked"] - 300
        data[0]["resumed_checkpoint_observations"] = data[0]["http_checked"] - 300
        data[3]["metadata_verification_complete"] = True
        data[3]["live_verified"] = 1
        for provider in data[4:]:
            provider.update(status="ok", rate_limited=False, queries_skipped=0)
        result = audit(*data)
        self.assertFalse(result["final_acceptance"])
        self.assertIn("INDEPENDENT_BROADCASTER_OWNERSHIP_NOT_VERIFIED",
                      result["tasks"]["15"]["blockers"])
        self.assertIn("INDEPENDENT_PLAYBACK_ACCEPTANCE_NOT_DOCUMENTED",
                      result["tasks"]["20"]["blockers"])

    def test_input_reports_cannot_be_trusted_when_malformed(self):
        data = list(evidence())
        data[1] = {"candidate_only": False}
        with self.assertRaises(InvalidEvidence):
            audit(*data)
        data = list(evidence())
        data[5]["queries_skipped"] = True
        with self.assertRaises(InvalidEvidence):
            audit(*data)


if __name__ == "__main__":
    unittest.main()
