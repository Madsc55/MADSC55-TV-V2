#!/usr/bin/env python3
"""Offline tests for the read-only pre-scan readiness decision."""
import unittest
import json
from unittest.mock import patch
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

    def test_pending_blocker_is_reported_without_changing_gate(self):
        entries = [{"id": i, "status": "completed"} for i in REQUIRED]
        entry = next(item for item in entries if item["id"] == min(REQUIRED))
        entry.update(status="in_progress", blocker="Independent restore evidence missing")
        result = inspect(ledger(entries))
        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"], [{"id": min(REQUIRED), "status": "in_progress",
                                               "blocker": "Independent restore evidence missing"}])

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

    def test_live_discovery_blocked_before_network(self):
        import discovery_34
        with patch("sys.argv", ["discovery_34.py", "--network"]), \
             patch("prescan_readiness_gate.inspect", return_value={"ready": False, "pending": [34]}), \
             patch("discovery_34.fetch_with_retry") as fetch:
            with self.assertRaises(SystemExit):
                discovery_34.main()
            fetch.assert_not_called()

    def test_live_scan_is_not_its_own_prerequisite(self):
        import json
        from prescan_readiness_gate import STATE
        state = json.loads(STATE.read_text(encoding="utf-8"))
        report = inspect(state)
        completed = {row["id"] for row in state["statuses"] if row["status"] == "completed"}
        self.assertNotIn(34, REQUIRED)
        self.assertEqual(report["ready"], REQUIRED <= completed)

    def test_offline_discovery_does_not_require_readiness(self):
        import discovery_34
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            output = str(Path(tmp) / "offline.json")
            with patch("sys.argv", ["discovery_34.py", "--output", output]), \
                 patch("discovery_34.fetch_with_retry") as fetch:
                discovery_34.main()
                fetch.assert_not_called()
            self.assertEqual(json.loads(Path(output).read_text())["mode"], "offline")

    def test_unknown_status_blocks(self):
        entries = [{"id": i, "status": "completed"} for i in REQUIRED]
        entries[0]["status"] = "unknown"
        self.assertFalse(inspect(ledger(entries))["ready"])

if __name__ == "__main__":
    unittest.main()
