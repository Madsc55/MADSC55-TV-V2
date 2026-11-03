#!/usr/bin/env python3
"""Batch unit checks for read-only source integration acceptance."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_integration_gate as gate


class IntegrationGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.config = root / "sources.json"
        self.reports = {k: root / (k + ".json") for k in gate.REPORTS}
        self.p1 = patch.object(gate, "CONFIG", self.config)
        self.p2 = patch.object(gate, "REPORTS", self.reports)
        self.p1.start()
        self.p2.start()
        self.addCleanup(self.p1.stop)
        self.addCleanup(self.p2.stop)
        self.write_sources(sorted(gate.REQUIRED))
        for path in self.reports.values():
            path.write_text("{}", encoding="utf-8")

    def write_sources(self, ids):
        self.config.write_text(json.dumps({"sources": [
            {"id": item, "url": "https://example.org/" + item + ".m3u"}
            for item in ids
        ]}), encoding="utf-8")

    def test_complete_reference_handoff_is_not_av_approval(self):
        result = gate.audit()
        self.assertEqual(result["status"], "INTEGRATED_REFERENCES_NOT_AV_VERIFIED")
        self.assertFalse(result["av_verified"])
        self.assertFalse(result["ibo_device_verified"])
        self.assertFalse(result["errors"])

    def test_missing_static_source_fails(self):
        self.write_sources(sorted(gate.REQUIRED - {"iptv-org-az"}))
        self.assertIn("MISSING_STATIC_SOURCES", gate.audit()["errors"])

    def test_duplicate_source_id_fails(self):
        self.write_sources(sorted(gate.REQUIRED) + ["iptv-org"])
        self.assertIn("DUPLICATE_SOURCE_IDS", gate.audit()["errors"])

    def test_missing_adapter_report_fails(self):
        self.reports["youtube"].unlink()
        result = gate.audit()
        self.assertEqual(result["adapter_reports"]["youtube"], "MISSING")
        self.assertIn("INCOMPLETE_ADAPTER_HANDOFF", result["errors"])

    def test_invalid_adapter_report_fails(self):
        self.reports["document_platforms"].write_text("{", encoding="utf-8")
        self.assertEqual(gate.audit()["adapter_reports"]["document_platforms"], "INVALID")


if __name__ == "__main__":
    unittest.main()
