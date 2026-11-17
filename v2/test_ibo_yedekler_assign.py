#!/usr/bin/env python3
"""Pure unit checks for the YEDEKLER assignment ledger (no live streams)."""
import unittest
from ibo_yedekler_assign import commit, plan, rollback, initial_ledger, validate_ledger


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        self.records = [{"ordinal": i + 1003, "url_sha256": str(i)} for i in range(1, 18075)]
        self.ledger = initial_ledger("fixed-sha", self.records)

    def test_range_and_undo(self):
        changes = plan(self.ledger, self.records, 221, 458, "YABANCI")
        self.assertEqual(len(changes), 238)
        self.assertEqual(changes[0]["global_ordinal"], 1224)
        updated = commit(self.ledger, changes, 0)
        self.assertEqual(updated["assignments"]["221"], "YABANCI")
        restored = rollback(updated)
        self.assertEqual(restored["assignments"], {})
        self.assertEqual(self.ledger["assignments"], {})

    def test_out_of_range_and_stale_source(self):
        with self.assertRaises(ValueError):
            plan(self.ledger, self.records, 1, 18075, "TURK")
        with self.assertRaises(ValueError):
            validate_ledger(self.ledger, "different-sha", self.records)

    def test_reassignment(self):
        first = commit(self.ledger, plan(self.ledger, self.records, 1, 2, "TURK"), 0)
        second = commit(first, plan(first, self.records, 2, 3, "YABANCI"), 1)
        restored = rollback(second)
        self.assertEqual(restored["assignments"], {"1": "TURK", "2": "TURK"})


if __name__ == "__main__":
    unittest.main()
