#!/usr/bin/env python3
"""Offline regression checks for immutable historical worldwide AV crosswalk."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import historical_worldwide_av_crosswalk as module


class HistoricalWorldwideAVCrosswalkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.historical = self.base / "history.jsonl"
        self.world = self.base / "world.json"
        self.hashes = [format(i, "064x") for i in range(4955)]
        self.raw = b"".join((json.dumps({"url_sha256": h}) + "\n").encode()
                            for h in self.hashes)
        self.historical.write_bytes(self.raw)
        self.world.write_text(json.dumps({"candidates": [
            {"url_sha256": self.hashes[0], "status": "VIDEO_AUDIO_DECODED",
             "decoded": True, "video": True, "audio": True},
            {"url_sha256": self.hashes[1], "status": "VIDEO_ONLY",
             "decoded": False, "video": True, "audio": False},
            {"url_sha256": "f" * 64, "status": "VIDEO_AUDIO_DECODED",
             "decoded": True, "video": True, "audio": True},
        ]}))

    def run_crosswalk(self):
        with patch.object(module, "BASELINE_SHA256", hashlib.sha256(self.raw).hexdigest()), \
             patch.object(module, "inspect", return_value={"candidate_hashes": 3}):
            return module.crosswalk(self.historical, self.world)

    def test_exact_sha_only_and_no_false_av(self):
        result = self.run_crosswalk()
        self.assertEqual(result["historical_identities_preserved"], 4955)
        self.assertEqual(result["historical_exact_hash_matches"], 2)
        self.assertEqual(result["historical_exact_hash_av_decoded"], 1)
        self.assertEqual(result["historical_matched_without_av_proof"], 1)
        self.assertEqual(result["historical_not_in_worldwide_report"], 4953)
        self.assertEqual(len(result["historical_missing_worldwide_url_sha256"]), 4953)
        self.assertEqual(result["historical_missing_worldwide_url_sha256"], sorted(self.hashes[2:]))
        self.assertTrue(all(len(h) == 64 for h in result["historical_missing_worldwide_url_sha256"]))
        self.assertFalse(result["protected_playlist_modified"])
        self.assertFalse(result["ibo_device_verified"])

    def test_missing_and_matched_sha_partition_is_lossless(self):
        result = self.run_crosswalk()
        matched = set(result["historical_match_url_sha256"])
        missing = set(result["historical_missing_worldwide_url_sha256"])
        decoded = set(result["historical_decoded_url_sha256"])
        self.assertFalse(matched & missing)
        self.assertEqual(matched | missing, set(self.hashes))
        self.assertTrue(decoded <= matched)
        self.assertEqual(len(matched) + len(missing), 4955)
        self.assertEqual(len(decoded) + result["historical_matched_without_av_proof"],
                         len(matched))
        self.assertEqual(result["historical_not_in_worldwide_report"], len(missing))

    def test_tampered_historical_baseline_rejected(self):
        self.historical.write_bytes(self.raw + b" ")
        with self.assertRaises(ValueError):
            self.run_crosswalk()

    def test_worldwide_acceptance_failure_blocks_crosswalk(self):
        with patch.object(module, "BASELINE_SHA256", hashlib.sha256(self.raw).hexdigest()), \
             patch.object(module, "inspect", side_effect=ValueError("bad sealed digest")):
            with self.assertRaisesRegex(ValueError, "bad sealed digest"):
                module.crosswalk(self.historical, self.world)

    def test_symlink_baseline_rejected(self):
        alias = self.base / "alias.jsonl"
        alias.symlink_to(self.historical)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            module.crosswalk(alias, self.world)


if __name__ == "__main__":
    unittest.main()
