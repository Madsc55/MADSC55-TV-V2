"""Regression checks for the read-only Stage A acceptance gate."""
import copy
import unittest
from v2.stage_a_evidence_review import audit, InvalidEvidence


def evidence():
    scan = {
        "mock_data_used": False, "archive_restore_test_passed": True,
        "http_checked": 10, "unique_new_candidates": 10,
        "av_verified": 4, "av_verified_this_run": 1,
        "resumed_decoded_av_evidence": 3,
        "http_checked_this_run": 2, "resumed_checkpoint_observations": 8,
        "unverified_or_failed_candidates": 6,
        "retried_failed_checkpoint_urls": 1,
        "recovered_av_from_failed_checkpoint": 1,
        "source_count": 1, "fetched_sources": 1,
        "status": "READY_FOR_DEVICE_TEST",
        "configured_sources_complete": True,
        "full_discovery_acceptance": True,
        "discovery_partial": False, "failed_sources": [], "source_drops": [],
        "resolved_direct_candidate_count": 0,
    }
    epg = {"verified_exact_id_channels": 0,
           "name_hint_channels_not_exact_evidence": 2,
           "programmes": 3, "candidate_only": True,
           "status": "EPG_CANDIDATE_FOR_REVIEW", "channels": 2}
    integrity = {"status_counts": {"XMLTV_VALID": 5}}
    youtube = {"videos_checked": 3, "live_verified": 0,
               "verification_failure_categories": {"SIGN_IN_REQUIRED": 3}}
    adapter = {"status": "rate_limited", "rate_limited": True,
               "queries_checked": 1, "queries_skipped": 2}
    return [scan, epg, integrity, youtube, adapter, copy.deepcopy(adapter)]


class StageAAuditTests(unittest.TestCase):
    def test_real_partial_scan_never_closes_tasks(self):
        result = audit(*evidence())
        self.assertFalse(result["final_acceptance"])
        self.assertEqual(set(result["tasks"]), {"15", "17", "18", "19", "20", "21"})
        self.assertTrue(all(t["status"] == "in_progress" for t in result["tasks"].values()))
        self.assertEqual(result["scan"]["av_decoded_total"], 4)
        self.assertIn("NO_EXACT_XMLTV_CHANNEL_ID_EVIDENCE", result["tasks"]["19"]["blockers"])

    def test_mock_scan_rejected(self):
        docs = evidence()
        docs[0]["mock_data_used"] = True
        with self.assertRaises(InvalidEvidence):
            audit(*docs)

    def test_unbalanced_av_rejected(self):
        docs = evidence()
        docs[0]["av_verified"] = 5
        with self.assertRaises(InvalidEvidence):
            audit(*docs)

    def test_unbalanced_resume_rejected(self):
        docs = evidence()
        docs[0]["resumed_checkpoint_observations"] = 7
        with self.assertRaises(InvalidEvidence):
            audit(*docs)

    def test_fake_epg_exact_evidence_rejected(self):
        docs = evidence()
        docs[1]["verified_exact_id_channels"] = 3
        with self.assertRaises(InvalidEvidence):
            audit(*docs)

    def test_archive_restore_required(self):
        docs = evidence()
        docs[0]["archive_restore_test_passed"] = False
        with self.assertRaises(InvalidEvidence):
            audit(*docs)


if __name__ == "__main__":
    unittest.main()
