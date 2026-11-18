#!/usr/bin/env python3
"""Offline tests for the read-only pre-scan readiness decision."""
import unittest
from prescan_readiness_gate import REQUIRED, inspect


def ledger(statuses):
    return {"schema": 1, "canonical_state": "state.json", "statuses": statuses}

class PreScanGateTests(unittest.TestCase):
    def test_all_completed(self):
        result = inspect(ledger([{"id": i, "status": "completed"} for i in REQUIRED]))
        self.assertTrue(result["ready"])
        self.assertEqual(result["pending"], [])
        self.assertEqual(result["missing"], [])

    def test_one_pending_blocks(self):
        entries = [{"id": i, "status": "completed"} for i in REQUIRED]
        entries[0]["status"] = "in_progress"
        self.assertFalse(inspect(ledger(entries))["ready"])

    def test_missing_blocks(self):
        self.assertFalse(inspect(ledger([]))["ready"])

    def test_duplicate_ids_block(self):
        entries = [{"id": i, "status": "completed"} for i in REQUIRED]
        entries.append(dict(entries[0]))
        self.assertEqual(inspect(ledger(entries))["error"], "DUPLICATE_TASK_ID")

    def test_invalid_entry_blocks(self):
        self.assertEqual(inspect(ledger([None]))["error"], "INVALID_ENTRY")

    def test_invalid_statuses_blocks(self):
        self.assertEqual(inspect(ledger({}))["error"], "INVALID_STATUSES")

    def test_noncanonical_state_blocks(self):
        self.assertEqual(inspect({})["error"], "INVALID_STATE_SCHEMA")
        self.assertEqual(inspect(None)["error"], "INVALID_STATE_SCHEMA")

    def test_unknown_status_blocks(self):
        entries = [{"id": i, "status": "completed"} for i in REQUIRED]
        entries[0]["status"] = "unknown"
        self.assertFalse(inspect(ledger(entries))["ready"])

if __name__ == "__main__":
    unittest.main()
