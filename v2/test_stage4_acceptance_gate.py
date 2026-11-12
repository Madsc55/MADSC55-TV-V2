#!/usr/bin/env python3
"""Stage 4 gate regression tests; fixture evidence is NEVER production proof."""
import unittest
import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from stage4_acceptance_gate import check, verify_local_artifacts

class GateTests(unittest.TestCase):
    def test_missing_proof_fails_closed(self):
        self.assertTrue(check({}))
    def test_partial_prerequisites_fail(self):
        self.assertTrue(check({"repository": "Madsc55/MADSC55-TV-V2", "prerequisites": {"9": {"status": "verified"}}}))
    def test_synthetic_fixture_not_treated_as_complete(self):
        sample = {"repository": "Madsc55/MADSC55-TV-V2", "main_ibo_unchanged": True,
                  "prerequisites": {k: {"status": "verified", "actions_run": "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/1"} for k in ("9", "13", "23")}}
        self.assertTrue(check(sample))

    def test_artifact_hashing_uses_file_stream(self):
        """Regression: acceptance must not call Path.read_bytes on artifact files."""
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "proof.bin"
            artifact.write_bytes(b"proof" * 1000)
            manifest = root / "manifest.json"
            sample = {"discovery": {"artifact_file": "proof.bin",
                                    "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}}
            with patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded read")):
                self.assertEqual(verify_local_artifacts(sample, manifest), [])

    def test_complete_looking_manifest_cannot_pass_without_independent_verification(self):
        run = "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"
        sample = {"repository": "Madsc55/MADSC55-TV-V2", "main_ibo_unchanged": True,
                  "prerequisites": {k: {"status": "verified", "actions_run": run} for k in ("9", "13", "23")}}
        for key in ("discovery", "recovery", "real_video_audio", "encrypted_archive", "s3_restore", "end_to_end"):
            sample[key] = {"status": "verified", "actions_run": run, "artifact_sha256": "a" * 64}
        self.assertEqual(check(sample), [])
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(json.dumps(sample), encoding="utf-8")
            for key in ("discovery", "recovery", "real_video_audio", "encrypted_archive", "s3_restore", "end_to_end"):
                sample[key]["artifact_file"] = key + ".log"
                payload = ("fixture-" + key).encode()
                (Path(directory) / (key + ".log")).write_bytes(payload)
                sample[key]["artifact_sha256"] = hashlib.sha256(payload).hexdigest()
            manifest.write_text(json.dumps(sample), encoding="utf-8")
            self.assertEqual(verify_local_artifacts(sample, manifest), [])
            sample["s3_restore"]["artifact_file"] = "../escape.log"
            self.assertTrue(verify_local_artifacts(sample, manifest))
            sample["s3_restore"]["artifact_file"] = "s3_restore.log"
            sample["s3_restore"]["artifact_sha256"] = "a" * 64
            self.assertTrue(verify_local_artifacts(sample, manifest))
            sample["s3_restore"]["artifact_sha256"] = hashlib.sha256(b"fixture-s3_restore").hexdigest()
            manifest.write_text(json.dumps(sample), encoding="utf-8")
            process = subprocess.run([sys.executable, str(Path(__file__).with_name("stage4_acceptance_gate.py")), str(manifest)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertIn("independent evidence verification", process.stderr)

if __name__ == "__main__":
    unittest.main()
