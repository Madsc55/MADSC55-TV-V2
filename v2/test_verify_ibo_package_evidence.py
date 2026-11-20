#!/usr/bin/env python3
"""Offline regression checks for Stage B encrypted evidence gate."""
import json
import hashlib
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_archive import encrypt
from export_ibo_batches import render
from verify_ibo_package_evidence import verify, zip_sha256

SECRET = "test-only-not-a-production-secret-2026"


class StageBPackageGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "evidence.zip"
        self.records = [
            {"url": "https://example.org/a.m3u8", "name": "A", "group": "TR",
             "http_hls_status": "AV_VERIFIED", "decoded_av_verified": True, "decode_status": "DECODED_AV"},
            {"url": "https://example.org/b.m3u8", "name": "B", "group": "AZ",
             "http_hls_status": "AV_VERIFIED", "decoded_av_verified": True, "decode_status": "DECODED_AV"},
        ]

    def build(self, tamper=False, report_count=2):
        raw = "".join(json.dumps(r) + "\n" for r in self.records).encode()
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("ibo-candidate-inventory.jsonl.enc", encrypt(raw, SECRET))
            z.writestr("ibo-real-scan-report.json", json.dumps({"av_verified": report_count}))
            for size in (1000, 2000):
                payload = render(self.records)
                if tamper and size == 1000:
                    payload = payload.replace(b"https://example.org/a.m3u8", b"https://example.org/wrong.m3u8")
                z.writestr(f"IBO_AV_VERIFIED_{size}_PART1.m3u8", payload)

    def test_zip_hash_matches_standard_sha256(self):
        self.build()
        expected = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(zip_sha256(self.path), expected)
        self.assertEqual(verify(self.path, SECRET)["zip_sha256"], expected)

    def test_exact_packages_pass(self):
        self.build()
        self.assertEqual(verify(self.path, SECRET)["result"], "PASS")

    def test_tampered_playlist_fails(self):
        self.build(tamper=True)
        self.assertEqual(verify(self.path, SECRET)["result"], "FAIL")

    def test_report_count_mismatch_fails(self):
        self.build(report_count=3)
        self.assertEqual(verify(self.path, SECRET)["result"], "FAIL")

    def test_empty_verified_inventory_fails_closed(self):
        self.records = []
        self.build(report_count=0)
        result = verify(self.path, SECRET)
        self.assertEqual(result["result"], "FAIL")
        self.assertTrue(any("No independently eligible" in error for error in result["errors"]))

    def test_oversized_zip_member_fails_before_decompression(self):
        from unittest.mock import patch
        self.build()
        with patch("verify_ibo_package_evidence.MAX_ZIP_MEMBER_BYTES", 8):
            with self.assertRaisesRegex(ValueError, "bounded verification budget"):
                verify(self.path, SECRET)

    def test_wrong_secret_fails(self):
        self.build()
        with self.assertRaises(Exception):
            verify(self.path, "another-valid-but-incorrect-secret")


if __name__ == "__main__":
    unittest.main()
