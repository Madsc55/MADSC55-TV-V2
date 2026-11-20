#!/usr/bin/env python3
"""Offline #497 adapter regression tests. No network or stream probing."""
import hashlib
import unittest
from unittest.mock import patch

from ibo_497_audit_adapter import convert


class ExistingAuditAdapterTests(unittest.TestCase):
    def setUp(self):
        self.blocks = [
            '#EXTINF:-1 group-title="YEDEKLER",Channel %d\nhttps://example.test/%d\n' % (i, i)
            for i in range(1, 1793)
        ]
        self.raw = ('#EXTM3U\n' + ''.join(self.blocks)).encode()
        self.results = [
            {"position": i, "name": "Channel %d" % i,
             "url_sha256": hashlib.sha256(("https://example.test/%d" % i).encode()).hexdigest(),
             "status": "AV_VERIFIED" if i <= 1107 else "PROBE_ERROR",
             "decoded_av_verified": i <= 1107,
             "classification": "WORKING" if i <= 1107 else "RECHECK_REQUIRED"}
            for i in range(1, 1793)
        ]
        self.audit = {"schema_version": 1, "category": "YEDEKLER",
                      "playlist_sha256": hashlib.sha256(self.raw).hexdigest(),
                      "total": 1792,
                      "counts": {"WORKING": 1107, "RECHECK_REQUIRED": 685},
                      "timestamp_utc": "2026-11-20T00:00:00Z",
                      "results": self.results}

    def test_verified_and_uncertain_only(self):
        report, evidence = convert(self.raw, self.audit, 1234)
        self.assertEqual(len(report["entries"]), 1792)
        self.assertEqual(sum(x["status"] == "verified" for x in report["entries"]), 1107)
        self.assertEqual(sum(x["status"] == "uncertain" for x in report["entries"]), 685)
        self.assertTrue(all(x["run_id"] == 1234 and x["evidence_sha256"] == evidence
                            for x in report["entries"]))

    def test_playlist_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            convert(self.raw + b"\n", self.audit, 1234)

    def test_url_hash_mismatch_fails_closed(self):
        self.audit["results"][1107]["url_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, 1234)

    def test_conflicting_verified_evidence_fails_closed(self):
        self.audit["results"][0]["decoded_av_verified"] = False
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, 1234)

    def test_missing_result_fails_closed(self):
        self.audit["results"].pop()
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, 1234)

    def test_invalid_run_id_fails_closed(self):
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, 0)


if __name__ == "__main__":
    unittest.main()
