#!/usr/bin/env python3
"""Public source inventory command is metadata-only and fail-closed on partial coverage."""
import unittest
from unittest.mock import patch
import run_public_inventory

class PublicInventoryTests(unittest.TestCase):
    def test_partial_inventory_is_nonzero(self):
        with patch("run_public_inventory.audit", return_value={
            "source_count": 2, "reachable_source_count": 1,
            "unreachable_source_count": 1, "results": []}), \
             patch("run_public_inventory.REPORT") as report, \
             patch("sys.argv", ["run_public_inventory.py", "--public-source-inventory"]):
            report.parent.mkdir.return_value = None
            with self.assertRaisesRegex(SystemExit, "partially unavailable"):
                run_public_inventory.main()
    def test_empty_inventory_is_not_success(self):
        with patch("run_public_inventory.audit", return_value={
            "source_count": 0, "reachable_source_count": 0,
            "unreachable_source_count": 0, "results": []}), \
             patch("run_public_inventory.REPORT") as report, \
             patch("sys.argv", ["run_public_inventory.py", "--public-source-inventory"]):
            with self.assertRaisesRegex(SystemExit, "partially unavailable"):
                run_public_inventory.main()

    def test_complete_inventory_succeeds(self):
        with patch("run_public_inventory.audit", return_value={
            "source_count": 1, "reachable_source_count": 1,
            "unreachable_source_count": 0, "results": []}), \
             patch("run_public_inventory.REPORT") as report, \
             patch("sys.argv", ["run_public_inventory.py", "--public-source-inventory"]):
            report.parent.mkdir.return_value = None
            run_public_inventory.main()
if __name__ == "__main__":
    unittest.main(verbosity=2)
