import unittest
from ibo_archive_operation_ledger import append, validate

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.op = {"operation_id": "batch-001", "before_sha256": "a"*64,
                   "after_sha256": "b"*64, "moved": 2500}

    def test_append_and_duplicate_rejection(self):
        records = append([], "a"*64, self.op)
        self.assertEqual(validate(records, "a"*64), "b"*64)
        with self.assertRaisesRegex(ValueError, "already processed"):
            append(records, "a"*64, self.op)

    def test_stale_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "Stale"):
            append([], "c"*64, self.op)

    def test_broken_chain_rejected(self):
        with self.assertRaisesRegex(ValueError, "chain"):
            validate([self.op], "c"*64)

    def test_oversized_batch_rejected(self):
        with self.assertRaisesRegex(ValueError, "batch"):
            append([], "a"*64, {**self.op, "moved": 2501})

if __name__ == "__main__":
    unittest.main()
