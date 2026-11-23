#!/usr/bin/env python3
"""Offline acceptance of full-playlist URL coverage, no network or mutations."""
import unittest
from full_playlist_url_audit import (
    MAX_SHARDS, SHARD_SIZE, batch, consolidate, index_playlist, safe_label,
)


def playlist(count):
    out = ["#EXTM3U"]
    for i in range(count):
        out += [
            f'#EXTINF:-1 tvg-id="id-{i}" group-title="ARCHIVE",Channel {i}',
            f"https://example.invalid/{i}.ts?auth=SECRET",
        ]
    return "\n".join(out) + "\n"


def offline_probe(_url):
    return {
        "status": "NOT_LIVE_TESTED", "programs": [], "sample_bytes": 0,
        "audio_video_decoded_verified": False,
        "distinct_broadcasters_verified": False,
    }


class FullPlaylistAuditTests(unittest.TestCase):
    def test_same_url_keeps_both_channel_records(self):
        data = (
            '#EXTM3U\n#EXTINF:-1 group-title="YEDEKLER",One\n'
            'https://example.invalid/live.ts?token=SECRET\n'
            '#EXTINF:-1 group-title="ANA ARŞİV",Two\n'
            'https://example.invalid/live.ts?token=SECRET\n'
        )
        total, urls = index_playlist(data)
        self.assertEqual(total, 2)
        self.assertEqual(len(urls), 1)
        report = batch(data, 0, probe=offline_probe)
        self.assertEqual(len(report["results"]), 1)
        self.assertEqual(len(report["results"][0]["channel_records"]), 2)
        self.assertNotIn("SECRET", str(report))
        self.assertFalse(report["results"][0]["safe_to_delete_or_merge"])

    def test_every_url_checked_once_across_all_shards(self):
        data = playlist(SHARD_SIZE + 1)
        results = [batch(data, i, probe=offline_probe) for i in range(MAX_SHARDS)]
        self.assertEqual(sum(len(x["results"]) for x in results), SHARD_SIZE + 1)
        self.assertEqual(sorted(len(x["results"]) for x in results)[-2:], [1, SHARD_SIZE])
        summary = consolidate(data, results)
        self.assertTrue(summary["audit_complete"])
        self.assertEqual(summary["unique_urls_reviewed"], SHARD_SIZE + 1)
        self.assertEqual(summary["missing_urls"], 0)
        self.assertEqual(summary["shards_present"], MAX_SHARDS)
        self.assertFalse(summary["broadcast_identity_verified"])
        self.assertFalse(summary["audio_video_decode_verified"])
        self.assertNotIn("SECRET", str(summary))

    def test_missing_shard_cannot_be_called_complete(self):
        data = playlist(1)
        results = [batch(data, i, probe=offline_probe) for i in range(MAX_SHARDS)]
        incomplete = consolidate(data, results[:-1])
        self.assertFalse(incomplete["audit_complete"])
        self.assertIn("MISSING_SHARDS", incomplete["issues"])

    def test_tampered_sha_cannot_be_accepted(self):
        data = playlist(1)
        results = [batch(data, i, probe=offline_probe) for i in range(MAX_SHARDS)]
        results[0]["playlist_sha256"] = "0" * 64
        summary = consolidate(data, results)
        self.assertFalse(summary["audit_complete"])
        self.assertEqual(summary["missing_urls"], 1)
        self.assertIn("STALE_OR_INVALID_SHARD", summary["issues"])

    def test_sensitive_channel_label_redaction(self):
        self.assertEqual(safe_label("https://secret.example/?token=SECRET"),
                         "[redacted]")
        self.assertEqual(safe_label("News HD"), "News HD")

    def test_more_urls_than_all_shards_refused_not_truncated(self):
        with self.assertRaises(ValueError):
            batch(playlist(MAX_SHARDS * SHARD_SIZE + 1), 0,
                  probe=offline_probe)


if __name__ == "__main__":
    unittest.main()
