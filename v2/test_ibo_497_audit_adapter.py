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
            '#EXTINF:-1 group-title="YEDEKLER",Channel %d\\nhttps://example.test/%d\\n' % (i, i)
            for i in range(1, 1793)
        ]
        self.raw = ('#EXTM3U\\n' + ''.join(self.blocks)).encode()
        self.run_id = 987654
        self.entries = []
        for i, block in enumerate(self.blocks, 1):
            url = block.splitlines()[-1].strip()
            verified = i <= 1107
            self.entries.append({
                "ordinal": i,
                "channel_sha256": sha(block.encode()),
                "url_sha256": sha(url.encode()),
                "run_id": self.run_id,
                "evidence_sha256": sha(("evidence-%d" % i).encode()),
                "attempts": 1,
                "repeatable_av_failure": False,
                "status": "verified" if verified else "uncertain",
                "probe_status": "AV_VERIFIED" if verified else "TIMEOUT",
                "decode_status": "DECODED_AV" if verified else "TIMEOUT",
                "evidence_level": "ffprobe_ffmpeg",
                "decoded_av_verified": verified,
            })
        self.audit = {
            "schema": 1,
            "playlist_sha256": sha(self.raw),
            "source_run_id": self.run_id,
            "source_commit": "a" * 40,
            "entries": self.entries,
            "counts": {"verified": 1107, "uncertain": 685},
            "read_only": True,
        }

    def test_real_producer_schema_maps_1107_and_685(self):
        report, evidence = convert(self.raw, self.audit, self.run_id)
        self.assertEqual(len(report["entries"]), 1792)
        self.assertEqual(sum(x["status"] == "verified" for x in report["entries"]), 1107)
        self.assertEqual(sum(x["status"] == "uncertain" for x in report["entries"]), 685)
        self.assertEqual(len(evidence), 64)

    def test_playlist_sha_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            convert(self.raw + b"\\n", self.audit, self.run_id)

    def test_reordered_ordinal_fails_closed(self):
        self.audit["entries"][0]["ordinal"] = 2
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_channel_identity_mismatch_fails_closed(self):
        self.audit["entries"][0]["channel_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_url_identity_mismatch_fails_closed(self):
        self.audit["entries"][0]["url_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_run_id_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id + 1)

    def test_failed_source_status_is_not_relabelled_uncertain(self):
        self.audit["entries"][1107]["status"] = "failed"
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_counts_must_match_exactly(self):
        self.audit["counts"]["verified"] = 1108
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)

    def test_unverified_av_claim_fails_closed(self):
        self.audit["entries"][0]["decoded_av_verified"] = False
        with self.assertRaises(ValueError):
            convert(self.raw, self.audit, self.run_id)


if __name__ == "__main__":
    unittest.main()
