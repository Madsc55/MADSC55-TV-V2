#!/usr/bin/env python3
"""Offline regression suite for actual #60/#72 loss-recovery evidence contracts."""
import hashlib
import unittest

from real_historical_stage3 import recover


def sha(i):
    return hashlib.sha256(("fixture-history-%d" % i).encode()).hexdigest()


def aggregate(rows):
    return {"coverage_complete": True, "unique_tested": len(rows),
            "channel_results": rows}


def candidates(rows):
    return {"candidates_truncated": False,
            "total_unique_candidates": len(rows), "candidates": rows}


class RealHistoricalStage3Tests(unittest.TestCase):
    def test_lossless_hash_recovery_dedup_and_region(self):
        old = aggregate([
            {"url_sha256": sha(1), "playback": "VIDEO_DECODED", "source": "#60"},
            {"url_sha256": sha(2), "playback": "VIDEO_DECODED", "source": "#60"},
            {"url_sha256": sha(3), "playback": "NO_VIDEO_DECODED", "source": "#60"},
        ])
        new = aggregate([{"url_sha256": sha(2), "playback": "NO_VIDEO_DECODED"}])
        meta = candidates([{"url_sha256": sha(1), "tvg_id": "TRT1.tr"},
                           {"url_sha256": sha(2), "tvg_id": "News.az"},
                           {"url_sha256": sha(3), "name": "Unknown"}])
        records, summary = recover(old, new, meta, expected_missing=1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["url_sha256"], sha(1))
        self.assertEqual(records[0]["region_candidate"], "TR")
        self.assertEqual(summary["old_only_identities"], 2)
        self.assertEqual(summary["previously_decoded_not_in_new"], 1)
        self.assertEqual(summary["duplicate_hashes_in_preserved_view"], 0)
        self.assertTrue(all("url" not in row for row in records))
        self.assertFalse(records[0]["spoken_language_verified"])
        self.assertEqual(summary["real_stream_url_records_recovered"], 0)

    def test_incomplete_or_duplicate_history_refused(self):
        good = aggregate([{"url_sha256": sha(1), "playback": "VIDEO_DECODED"}])
        current = aggregate([])
        meta = candidates([{"url_sha256": sha(1)}])
        for invalid in (
            {"coverage_complete": False, "unique_tested": 1, "channel_results": good["channel_results"]},
            aggregate(good["channel_results"] * 2),
            {"coverage_complete": True, "unique_tested": 2, "channel_results": good["channel_results"]},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                recover(invalid, current, meta, expected_missing=1)
        with self.assertRaisesRegex(ValueError, "baseline"):
            recover(good, current, meta, expected_missing=4955)

    def test_missing_or_truncated_metadata_refused(self):
        good = aggregate([{"url_sha256": sha(1), "playback": "VIDEO_DECODED"}])
        with self.assertRaises(ValueError):
            recover(good, aggregate([]), candidates([{"url_sha256": sha(2)}]), expected_missing=1)
        with self.assertRaises(ValueError):
            recover(good, aggregate([]),
                    dict(candidates([{"url_sha256": sha(1)}]), candidates_truncated=True),
                    expected_missing=1)
        with self.assertRaises(ValueError):
            recover(good, aggregate([]),
                    candidates([{"url_sha256": sha(1), "url": "https://private.invalid/live.m3u8"}]),
                    expected_missing=1)

    def test_missing_with_unknown_region_remains_unclassified(self):
        old = aggregate([{"url_sha256": sha(4), "playback": "VIDEO_DECODED"}])
        rec, report = recover(old, aggregate([]), candidates([{
            "url_sha256": sha(4), "name": "Global news"
        }]), expected_missing=1)
        self.assertEqual(report["region_candidates"]["UNKNOWN"], 1)
        self.assertFalse(rec[0]["device_verified"])


if __name__ == "__main__":
    unittest.main()
