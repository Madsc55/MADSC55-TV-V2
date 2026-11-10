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

    def test_http_403_without_references_remains_accounted_for(self):
        blocked = [p for p in self.report["pages"] if p["status"] != "FETCHED"]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["page_id"], "trt-spor-official")
        self.assertEqual(blocked[0]["error"], "HTTP_403")
        self.assertEqual(verify(self.report)["pages_checked"], 27)


if __name__ == "__main__":
    unittest.main()
