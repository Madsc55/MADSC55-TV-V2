#!/usr/bin/env python3
"""Prove the permanent 4,955 REAL #60 historical identities cannot silently drift.

Checks public SHA256 metadata only. No stream URLs, network calls or playlist
modifications. This is an immutable, separately verified baseline.
"""
import hashlib
import json
from pathlib import Path
import re
import unittest
from collections import Counter

ARCHIVE = Path(__file__).resolve().parent / "history/stage3-4955-hash-only.jsonl"
BASELINE_FILE_SHA256 = "ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27"
BASELINE_IDENTITY_SHA256 = "e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83"
BASELINE_REGIONS = {"TR": 50, "AZ": 1, "UNKNOWN": 4904}
BASELINE_FIELDS = {
    "url_sha256", "source", "region_candidate", "classification_evidence",
    "playback_at_run60", "historical_not_reverified", "spoken_language_verified",
    "device_verified",
}


class ImmutableHistoryEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ARCHIVE.read_bytes()
        cls.rows = [json.loads(line) for line in cls.raw.decode("utf-8").splitlines() if line]

    def test_exact_original_real_history_content_and_identity_set(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), BASELINE_FILE_SHA256)
        self.assertEqual(len(self.rows), 4955)
        hashes = [r["url_sha256"] for r in self.rows]
        self.assertEqual(len(set(hashes)), 4955)
        self.assertEqual(hashlib.sha256("".join(sorted(hashes)).encode()).hexdigest(),
                         BASELINE_IDENTITY_SHA256)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", x) for x in hashes))

    def test_region_provenance_no_urls_no_playback_claims(self):
        self.assertEqual(dict(Counter(r["region_candidate"] for r in self.rows)),
                         BASELINE_REGIONS)
        self.assertEqual(dict(Counter(r["classification_evidence"] for r in self.rows)),
                         {"METADATA": 51, "NONE": 4904})
        for row in self.rows:
            self.assertEqual(set(row), BASELINE_FIELDS)
            self.assertNotIn("url", row)
            self.assertTrue(re.fullmatch(r"[A-Za-z0-9_.#-]{1,120}", row["source"]))
            self.assertEqual(row["playback_at_run60"], "VIDEO_DECODED")
            self.assertIs(row["historical_not_reverified"], True)
            self.assertIs(row["spoken_language_verified"], False)
            self.assertIs(row["device_verified"], False)


if __name__ == "__main__":
    unittest.main()
