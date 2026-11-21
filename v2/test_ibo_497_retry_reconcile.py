#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from ibo_497_retry_reconcile import build_full_report, digest

class RetryReconcileTests(unittest.TestCase):
    def test_initial_manifest_digest_is_required(self):
        with self.assertRaises(ValueError):
            build_full_report(b"#EXTM3U\n", {}, b"{}", {})

if __name__ == "__main__":
    unittest.main()
