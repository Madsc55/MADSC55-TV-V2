#!/usr/bin/env python3
"""Offline tests using the exact #495 producer schema; no stream probes."""
import hashlib
import unittest

from ibo_497_audit_adapter import convert


def sha(value):
    return hashlib.sha256(value).hexdigest()


class ExistingAuditAdapterTests(unittest.TestCase):
    def setUp(self):
        self.blocks = [
            '#EXTINF:-1 group-title="🗂️ YEDEKLER",Channel %d\nhttps://example.test/%d\n' % (i, i)
            for i in range(1, 1793)
        ]
        self.raw = ('#EXTM3U\n' + ''.join(self.blocks)).encode("utf-8")
        self.run_id = 987654
        self.results = []
        for i, block in enumerate(self.blocks, 1):
            url = block.splitlines()[-1].strip()
            working = i <= 1107
            self.results.append({
                "position": i,
                "name": "Channel %d" % i,
                "url_sha256": sha(url.encode("utf-8")),
                "status": "AV_VERIFIED" if working else "PROBE_ERROR",
                "video": working,
                "audio": working,
                "decoded_av_verified": working,
                "classification": "WORKING" if working else "RECHECK_REQUIRED",
            })
        self.audit = {
            "schema_version": 1,
            "timestamp_utc": "2026-11-20T00:20:09.490490+00:00",
            "playlist_sha256": sha(self.raw),
            "category": "YEDEKLER",
            "total": 1792,
            "counts": {"WORKING": 1107, "RECHECK_REQUIRED": 685},
            "results": self.results,
            "policy": "Read-only; failures need repeat verification.",
        }

    def test_real_producer_schema_maps_1107_and_685(self):
        report, evidence = convert(self.raw, self.audit, self.run_id)
        self.assertEqual(len(report["entries"]), 1792)
        self.assertEqual(sum(x["status"] == "verified" for x in report["entries"]), 1107)
        self.assertEqual(sum(x["status"] == "uncertain" for x in report["entries"]), 685)
        self.assertEqual(len(evidence), 64)

    def test_playlist_sha_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            convert(self.raw + b"\n", self.audit, self.run_id)

    def test_reordered_position_fails_closed(self):
        self.audit["results"][0]["position"] = 2
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_channel_name_mismatch_fails_closed(self):
        self.audit["results"][0]["name"] = "Different Channel"
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_url_identity_mismatch_fails_closed(self):
        self.audit["results"][0]["url_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_run_id_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id + 1)

    def test_failed_source_status_is_not_relabelled_uncertain(self):
        self.audit["results"][1107]["classification"] = "FAILED"
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_counts_must_match_exactly(self):
        self.audit["counts"]["WORKING"] = 1108
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_unverified_av_claim_fails_closed(self):
        self.audit["results"][0]["decoded_av_verified"] = False
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)


if __name__ == "__main__":
    unittest.main()
