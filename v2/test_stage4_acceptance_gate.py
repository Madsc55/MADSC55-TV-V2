#!/usr/bin/env python3
"""Stage 4 gate regression tests; fixture evidence is NEVER production proof."""
import unittest
import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from stage4_acceptance_gate import PROOFS, check, verify_local_artifacts

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
            manifest = root / "manifest.json"
            sample = {}
            for stage in PROOFS:
                artifact = root / (stage + ".bin")
                payload = stage.encode() * 1000
                artifact.write_bytes(payload)
                sample[stage] = {"artifact_file": artifact.name,
                                 "artifact_sha256": hashlib.sha256(payload).hexdigest()}
            with patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded read")):
                self.assertEqual(verify_local_artifacts(sample, manifest), [])

    def test_empty_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "empty.log").write_bytes(b"")
            sample = {"discovery": {"artifact_file": "empty.log",
                                    "artifact_sha256": hashlib.sha256(b"").hexdigest()}}
            self.assertTrue(any("empty artifact" in e for e in
                                verify_local_artifacts(sample, root / "manifest.json")))

    def test_same_artifact_cannot_prove_two_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"real-file-bytes-are-not-independent-proof"
            (root / "shared.log").write_bytes(payload)
            proof = {"artifact_file": "shared.log",
                     "artifact_sha256": hashlib.sha256(payload).hexdigest()}
            sample = {"discovery": dict(proof), "recovery": dict(proof)}
            self.assertTrue(any("reused" in e for e in
                                verify_local_artifacts(sample, root / "manifest.json")))

    def test_complete_looking_manifest_cannot_pass_without_independent_verification(self):
        run = "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/123"
        sample = {"repository": "Madsc55/MADSC55-TV-V2", "main_ibo_unchanged": True,
                  "prerequisites": {k: {"status": "verified", "actions_run": run} for k in ("9", "13", "23")}}
        for key in PROOFS:
            sample[key] = {"status": "verified", "actions_run": run, "artifact_sha256": "a" * 64}
        self.assertEqual(check(sample), [])
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(json.dumps(sample), encoding="utf-8")
            for key in PROOFS:
                sample[key]["artifact_file"] = key + ".log"
                payload = ("fixture-" + key).encode()
                (Path(directory) / (key + ".log")).write_bytes(payload)
                sample[key]["artifact_sha256"] = hashlib.sha256(payload).hexdigest()
            manifest.write_text(json.dumps(sample), encoding="utf-8")
            self.assertEqual(verify_local_artifacts(sample, manifest), [])
            sample["drive_restore"]["artifact_file"] = "../escape.log"
            self.assertTrue(verify_local_artifacts(sample, manifest))
            sample["drive_restore"]["artifact_file"] = "drive_restore.log"
            sample["drive_restore"]["artifact_sha256"] = "a" * 64
            self.assertTrue(verify_local_artifacts(sample, manifest))
            sample["drive_restore"]["artifact_sha256"] = hashlib.sha256(b"fixture-drive_restore").hexdigest()
            manifest.write_text(json.dumps(sample), encoding="utf-8")
            process = subprocess.run([sys.executable, str(Path(__file__).with_name("stage4_acceptance_gate.py")), str(manifest)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertIn("independent evidence verification", process.stderr)

if __name__ == "__main__":
    unittest.main()
