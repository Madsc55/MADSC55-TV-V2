#!/usr/bin/env python3
"""Regression tests for read-only official publisher source provenance."""
import copy
import json
from pathlib import Path
import unittest

from official_page_audit_guard import verify

REPORT = Path(__file__).resolve().parent / "reports/official-page-http-audit-20261109.json"


class OfficialPageAuditGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_actual_27_page_report_has_consistent_source_history(self):
        self.assertEqual(verify(self.report), {
            "pages_checked": 27,
            "pages_fetched": 26,
            "unique_reference_hashes": 68,
            "shared_reference_hashes": 15,
            "reference_source_associations": 83,
        })

    def test_missing_shared_page_association_is_detected(self):
        report = copy.deepcopy(self.report)
        page = next(p for p in report["pages"] if p.get("references"))
        page["references"].pop()
        with self.assertRaisesRegex(ValueError, "counter mismatch"):
            verify(report)

    def test_wrong_source_index_is_detected_when_counters_still_match(self):
        report = copy.deepcopy(self.report)
        shared = next(row for row in report["reference_sources"] if len(row["page_ids"]) > 1)
        shared["page_ids"].pop()
        with self.assertRaisesRegex(ValueError, "index disagrees with per-page evidence"):
            verify(report)

    def test_duplicate_page_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["pages"].append(copy.deepcopy(report["pages"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate page identity"):
            verify(report)

    def test_http_audit_cannot_claim_av_proof(self):
        report = copy.deepcopy(self.report)
        report["playback_verified"] = True
        with self.assertRaisesRegex(ValueError, "must not claim playback"):
            verify(report)

    def test_unknown_page_state_cannot_hide_a_failed_fetch(self):
        report = copy.deepcopy(self.report)
        page = next(p for p in report["pages"] if p["status"] != "FETCHED")
        page["status"] = "IGNORED"
        with self.assertRaisesRegex(ValueError, "Unknown official-page fetch status"):
            verify(report)

    def test_http_failure_must_preserve_error_reason(self):
        report = copy.deepcopy(self.report)
        page = next(p for p in report["pages"] if p["status"] != "FETCHED")
        page.pop("error")
        with self.assertRaisesRegex(ValueError, "missing explicit error provenance"):
            verify(report)

    def test_missing_fetched_page_digest_is_rejected(self):
        report = copy.deepcopy(self.report)
        page = next(p for p in report["pages"] if p["status"] == "FETCHED")
        page.pop("html_sha256")
        with self.assertRaisesRegex(ValueError, "missing content digest"):
            verify(report)

    def test_unfetched_page_cannot_claim_discovered_sources(self):
        report = copy.deepcopy(self.report)
        page = next(p for p in report["pages"] if p["status"] != "FETCHED")
        page["references"] = ["0" * 64]
        with self.assertRaisesRegex(ValueError, "Unfetched page"):
            verify(report)

    def test_http_403_without_references_remains_accounted_for(self):
        blocked = [p for p in self.report["pages"] if p["status"] != "FETCHED"]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["page_id"], "trt-spor-official")
        self.assertEqual(blocked[0]["error"], "HTTP_403")
        self.assertEqual(verify(self.report)["pages_checked"], 27)


if __name__ == "__main__":
    unittest.main()
