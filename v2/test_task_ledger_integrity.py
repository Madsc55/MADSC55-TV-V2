#!/usr/bin/env python3
"""Validate the restored historical task ledger without promoting acceptance."""
import json
import unittest
from pathlib import Path

LEDGER = Path(__file__).resolve().parent / "tasks" / "state.json"

class TaskLedgerIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_all_34_ids_are_unique_and_present(self):
        ids = [row["id"] for row in self.ledger["statuses"]]
        self.assertEqual(ids, list(range(1, 35)))

    def test_statuses_are_allowed(self):
        allowed = set(self.ledger["allowed_statuses"])
        self.assertEqual(allowed, {"pending", "in_progress", "blocked", "completed"})
        for row in self.ledger["statuses"]:
            with self.subTest(id=row["id"]):
                self.assertIn(row["status"], allowed)
                self.assertIsInstance(row.get("evidence_urls"), list)

    def test_snapshot_is_explicitly_historical(self):
        self.assertEqual(self.ledger["schema"], 1)
        self.assertIn("historical", self.ledger["note"].lower())
        self.assertTrue(self.ledger["generated_at"])
        self.assertTrue(self.ledger["observed_commit"])

if __name__ == "__main__":
    unittest.main()
