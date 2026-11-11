#!/usr/bin/env python3
"""Stage 4 gate regression tests; fixture evidence is NEVER production proof."""
import unittest
from stage4_acceptance_gate import check

class GateTests(unittest.TestCase):
    def test_missing_proof_fails_closed(self):
        self.assertTrue(check({}))
    def test_partial_prerequisites_fail(self):
        self.assertTrue(check({"repository": "Madsc55/MADSC55-TV-V2", "prerequisites": {"9": {"status": "verified"}}}))
    def test_synthetic_fixture_not_treated_as_complete(self):
        sample = {"repository": "Madsc55/MADSC55-TV-V2", "main_ibo_unchanged": True,
                  "prerequisites": {k: {"status": "verified", "actions_run": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/1"} for k in ("9", "13", "23")}}
        self.assertTrue(check(sample))

if __name__ == "__main__":
    unittest.main()
