#!/usr/bin/env python3
"""Stage 4 gate regression tests; fixture evidence is NEVER production proof."""
import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
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
            process = subprocess.run([sys.executable, str(Path(__file__).with_name("stage4_acceptance_gate.py")), str(manifest)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertIn("independent evidence verification", process.stderr)

if __name__ == "__main__":
    unittest.main()
