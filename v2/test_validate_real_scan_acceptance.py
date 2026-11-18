#!/usr/bin/env python3
"""Offline fail-closed regression tests; no private data or internet access."""
import copy
import unittest

from validate_real_scan_acceptance import ScanIncomplete, require_complete_adapters, validate_report


def complete_report():
    return {
        "mock_data_used": False,
        "full_discovery_acceptance": True,
        "configured_sources_complete": True,
        "discovery_partial": False,
        "failed_sources": [], "source_drops": [],
        "mandatory_failed_sources": [], "optional_failed_discovered_sources": [],
        "mandatory_source_drops": [], "optional_discovery_source_drops": [],
        "archive_restore_test_passed": True,
        "status": "READY_FOR_DEVICE_TEST",
        "source_count": 3, "fetched_sources": 3,
        "unique_new_candidates": 5,
        "http_checked": 5, "http_checked_this_run": 2,
        "resumed_checkpoint_observations": 3,
        "av_verified": 3, "av_verified_this_run": 1,
        "resumed_decoded_av_evidence": 2,
        "unverified_or_failed_candidates": 2,
        "candidate_inventory": "/runner/v2/reports/ibo-candidate-inventory.jsonl.enc",
        "written_parts": ["/runner/v2/reports/IBO_YENI_ADAYLAR.m3u8"],
        "playback_verified_on_device": False,
    }


class RealScanAcceptanceTests(unittest.TestCase):
    def test_deferred_failures_prevent_acceptance_even_with_balanced_totals(self):
        for count in (1, -1, False, "0", None):
            with self.subTest(count=count), self.assertRaises(ScanIncomplete):
                validate_report({**complete_report(), "deferred_archived_failures": count})
        validate_report({**complete_report(), "deferred_archived_failures": 0})

    def test_complete_real_scan_is_not_final_device_approval(self):
        result = validate_report(complete_report())
        self.assertEqual(result["status"], "COMPLETE_REAL_SCAN_NOT_FINAL_DEVICE_ACCEPTANCE")
        self.assertEqual(result["decoded_av_previous_checkpoint"], 2)
        self.assertEqual(result["decoded_av_this_run"], 1)

    def test_green_actions_partial_report_must_fail(self):
        report = complete_report()
        report.update({
            "status": "PARTIAL_DISCOVERY_EVIDENCE_ONLY",
            "full_discovery_acceptance": False,
            "discovery_partial": True, "source_count": 5, "fetched_sources": 3,
            "optional_failed_discovered_sources": [
                {"id": "integrated-m3u-example", "error": "HTTPError"}],
            "candidate_inventory": "/runner/v2/reports/ibo-candidate-inventory.jsonl.pending.enc",
            "written_parts": [],
        })
        with self.assertRaisesRegex(ScanIncomplete, "Discovery is incomplete"):
            validate_report(report)

    def test_partial_prior_av_evidence_is_not_promoted(self):
        original = complete_report()
        for field, value in (
            ("status", "PARTIAL_DISCOVERY_EVIDENCE_ONLY"),
            ("archive_restore_test_passed", False),
            ("mock_data_used", True),
            ("http_checked_this_run", 3),
            ("resumed_decoded_av_evidence", 3),
            ("candidate_inventory", "/runner/v2/reports/ibo-candidate-inventory.jsonl.pending.enc"),
            ("written_parts", []),
            ("playback_verified_on_device", True),
        ):
            with self.subTest(field=field):
                payload = copy.deepcopy(original)
                payload[field] = value
                with self.assertRaises(ScanIncomplete):
                    validate_report(payload)

    def test_mismatched_counts_and_missing_sources_fail(self):
        original = complete_report()
        for field, value in (
            ("source_count", 4),
            ("fetched_sources", 2),
            ("http_checked", 1),
            ("av_verified", 0),
            ("unverified_or_failed_candidates", 1),
            ("mandatory_failed_sources", [{"id": "primary", "error": "HTTPError"}]),
            ("optional_failed_discovered_sources", [{"id": "discovery", "error": "ValueError"}]),
            ("source_drops", [{"id": "primary"}]),
            ("discovery_partial", True),
            ("full_discovery_acceptance", False),
        ):
            with self.subTest(field=field):
                payload = copy.deepcopy(original)
                payload[field] = value
                with self.assertRaises(ScanIncomplete):
                    validate_report(payload)

    def test_malformed_or_duplicate_test_parts_fail(self):
        for parts in ([""], [None], [123], ["not-a-playlist.txt"],
                      ["a.m3u8", "a.m3u8"], ["bad" + chr(0) + ".m3u8"]):
            with self.subTest(parts=parts):
                payload = complete_report()
                payload["written_parts"] = parts
                with self.assertRaises(ScanIncomplete):
                    validate_report(payload)

    def test_corrupt_or_boolean_counts_fail(self):
        for report in (None, [], {}, {"status": "READY_FOR_DEVICE_TEST"}):
            with self.assertRaises(ScanIncomplete):
                validate_report(report)
        payload = complete_report()
        payload["av_verified"] = True
        with self.assertRaises(ScanIncomplete):
            validate_report(payload)

    def test_adapter_evidence_is_required_even_for_a_complete_core_scan(self):
        provider = {"status": "ok", "rate_limited": False, "errors": [],
                    "queries_total": 12, "queries_checked": 12,
                    "queries_failed": 0, "queries_skipped": 0}
        reports = {
            "repositories": {"mode": "network", "candidates": [], "errors": []},
            "github_m3u": {"sources": [], "errors": []},
            "gitlab": dict(provider),
            "codeberg": dict(provider),
            "official": {"scope": "WORLDWIDE", "channels": [{"name": "Example"}]},
            "youtube": {"metadata_verification_complete": True, "errors": [],
                        "videos_checked": 3, "live_verified": 1},
        }
        scan = {**complete_report(), "resolved_direct_candidate_count": 1}
        require_complete_adapters(scan, reports)
        reports["codeberg"].update(status="error", rate_limited=True,
                                   queries_checked=1, queries_failed=1, queries_skipped=11)
        reports["youtube"].update(metadata_verification_complete=False, live_verified=0)
        scan["resolved_direct_candidate_count"] = 0
        validate_report(scan)
        with self.assertRaisesRegex(ScanIncomplete, "codeberg, YouTube .*direct streams"):
            require_complete_adapters(scan, reports)


if __name__ == "__main__":
    unittest.main()
