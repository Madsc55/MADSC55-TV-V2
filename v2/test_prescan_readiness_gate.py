#!/usr/bin/env python3
"""Offline tests for the read-only pre-scan readiness decision."""
import unittest
from prescan_readiness_gate import REQUIRED, inspect

class PreScanGateTests(unittest.TestCase):
    def test_all_completed(self):
        result = inspect({"statuses": [{"id": i, "status": "completed"} for i in REQUIRED]})
        self.assertTrue(result["ready"])
        self.assertEqual(result["pending"], [])
        self.assertEqual(result["missing"], [])

    def test_one_pending_blocks(self):
        entries = [{"id": i, "status": "completed"} for i in REQUIRED]
        entries[0]["status"] = "in_progress"
        self.assertFalse(inspect({"statuses": entries})["ready"])

    def test_missing_blocks(self):
        self.assertFalse(inspect({"statuses": []})["ready"])

    def test_unknown_status_blocks(self):
        entries = [{"id": i, "status": "completed"} for i in REQUIRED]
        entries[0]["status"] = "unknown"
        self.assertFalse(inspect({"statuses": entries})["ready"])

if __name__ == "__main__":
    unittest.main()
