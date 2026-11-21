import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from v2.backup_smart_archive import build_report, main

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

    def test_string_true_is_not_verified_language(self):
        result = build_report([row(1, language="TR", language_evidence_verified="true")], 1)["channels"][0]
        self.assertEqual(result["language"], "UNKNOWN")

    def test_string_true_is_not_verified_av(self):
        result = build_report([row(1, health="WORKING", decoded_av_verified="true")], 1)["channels"][0]
        self.assertEqual(result["health"], "UNKNOWN")

    def test_terminal_failure_requires_verified_evidence(self):
        result = build_report([row(1, health="NOT_WORKING", retries_exhausted=True)], 1)["channels"][0]
        self.assertEqual(result["health"], "UNKNOWN")
        verified = build_report([row(1, health="NOT_WORKING", retries_exhausted=True, terminal_failure_verified=True)], 1)["channels"][0]
        self.assertEqual(verified["health"], "NOT_WORKING")

    def test_current_inventory_without_historical_count(self):
        self.assertEqual(build_report([row(1), row(2)])["total"], 2)
        with self.assertRaises(ValueError):
            build_report([])
        with self.assertRaises(ValueError):
            build_report([row(1)], 18074)

    def test_existing_report_is_never_overwritten(self):
        with TemporaryDirectory() as folder:
            evidence = Path(folder) / "evidence.json"
            protected = Path(folder) / "existing.m3u8"
            evidence.write_text(json.dumps({"channels":[row(1)]}), encoding="utf-8")
            protected.write_text("KEEP_ORIGINAL_PLAYLIST", encoding="utf-8")
            with patch.object(sys, "argv", [
                "archive", "--evidence", str(evidence), "--output", str(protected),
                "--expected-count", "1"
            ]):
                with self.assertRaises(FileExistsError):
                    main()
            self.assertEqual(protected.read_text(encoding="utf-8"), "KEEP_ORIGINAL_PLAYLIST")

    def test_string_true_does_not_exhaust_retries(self):
        result = build_report([row(1, health="NOT_WORKING", retries_exhausted="true")], 1)["channels"][0]
        self.assertEqual(result["health"], "UNKNOWN")

if __name__ == "__main__":
    unittest.main()
