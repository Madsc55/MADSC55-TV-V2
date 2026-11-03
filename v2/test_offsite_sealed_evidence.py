#!/usr/bin/env python3
"""Offline sealed offsite backup evidence regression; no real RSA key embedded."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from verify_drive_sealed_evidence import MANIFEST, BASELINE, verify

class OffsiteEvidenceTests(unittest.TestCase):
    def test_real_baseline_and_manifest_preserve_4955_identity_hashes(self):
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        raw = BASELINE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), m["historic_rows_sha256"])
        rows = [json.loads(line) for line in raw.splitlines() if line]
        self.assertEqual(len(rows), 4955)
        self.assertEqual(len({r["url_sha256"] for r in rows}), 4955)
        self.assertEqual(m["orphan_unique_metadata_identities"], 50)
        self.assertEqual(m["orphan_source_occurrences"], 55)
        self.assertIs(m["encrypted_url_decryption_verified"], False)
        self.assertIs(m["production_acceptance_complete"], False)
    def test_manifest_tracks_exact_original_and_independent_sha(self):
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(m["encrypted_artifact_checks"]), 2)
        for item in m["encrypted_artifact_checks"]:
            self.assertEqual(item["source_zip_sha256"], item["drive_readback_sha256"])
            self.assertEqual(len(item["source_zip_sha256"]), 64)
        self.assertEqual(m["encrypted_artifact_checks"][0]["sealed_record_counts"]["stage3-git-history-recovered.sealed"], 4902)
        self.assertEqual(m["encrypted_artifact_checks"][1]["sealed_record_counts"]["three-source-all-historical-candidates.sealed"], 107)
    def test_reject_missing_remote_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((FileNotFoundError, OSError)):
                verify(Path(directory)/"not-downloaded.zip", Path(directory)/"also-missing.zip")

if __name__=="__main__":
    unittest.main(verbosity=2)
