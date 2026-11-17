import hashlib
import unittest
from v2.backup_smart_archive import build_report

def row(n, **kwargs):
    return {"url_sha256": hashlib.sha256(str(n).encode()).hexdigest(), **kwargs}

class SmartArchiveTests(unittest.TestCase):
    def test_verified_turkish_working(self):
        report = build_report([row(1, language="TR", health="WORKING",
            language_evidence_verified=True, decoded_av_verified=True)], 1)
        self.assertEqual(report["counts"]["TURK_WORKING"], 1)

    def test_metadata_only_not_language_proof(self):
        result = build_report([row(1, language="TR", health="WORKING",
            decoded_av_verified=True)], 1)["channels"][0]
        self.assertEqual(result["category"], "UNCERTAIN")
        self.assertTrue(result["manual_review"])

    def test_single_failure_not_dead(self):
        result = build_report([row(1, language="FOREIGN", health="NOT_WORKING",
            language_evidence_verified=True)], 1)["channels"][0]
        self.assertEqual(result["health"], "UNKNOWN")
        self.assertTrue(result["retry"])

    def test_complete_inventory_required(self):
        with self.assertRaises(ValueError):
            build_report([row(1)], 18074)

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            build_report([row(1), row(1)], 2)

    def test_invalid_evidence_rejected(self):
        with self.assertRaises(ValueError):
            build_report([row(1, language="MAYBE")], 1)

if __name__ == "__main__":
    unittest.main()
