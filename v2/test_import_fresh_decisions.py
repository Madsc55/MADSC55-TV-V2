import unittest
from import_fresh_decisions import attach


class DecisionImportTests(unittest.TestCase):
    def test_two_dates_multiple_positions_and_replay(self):
        positive = {"decoded_av_verified": True}
        row = {"url_sha256": "same", "result": positive, "checked_at": 5,
               "diagnostics": {"old": "preserved"}, "recovery_attempts": 2}
        old = {"first": row, "other": {**row, "url_sha256": "other"}}
        evidence = {"same": {"1/5": {"run_id": 1}, "1/6": {"run_id": 1},
                             "2/5": {"run_id": 2}}, "unmatched": {"1/8": {"run_id": 1}}}
        rows, matched, inserted = attach(old, evidence)
        self.assertEqual(set(rows), set(old))
        self.assertEqual(matched, {"same"})
        self.assertEqual(inserted, {"1": 2, "2": 1})
        self.assertEqual(rows["first"], {**row, "diagnostics": {"old": "preserved", "fresh_av_history": evidence["same"]}})
        self.assertEqual(old["first"]["diagnostics"], {"old": "preserved"})
        self.assertIs(rows["other"], old["other"])
        self.assertEqual(attach(rows, evidence), (rows, matched, {}))
        with self.assertRaisesRegex(ValueError, "differs"):
            attach(rows, {"same": {"1/5": {"run_id": 2}}})
