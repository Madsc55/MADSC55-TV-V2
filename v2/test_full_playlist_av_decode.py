#!/usr/bin/env python3
"""No-network tests of SHA-bound full-playlist decoded A/V review."""
import subprocess
import unittest
from unittest.mock import patch

from full_playlist_url_audit import (
    MAX_SHARDS, SHARD_SIZE, POLICY as PRIOR_POLICY, index_playlist
)
from full_playlist_av_decode import (
    POLICY, SOURCE_RUN_ID, batch, consolidate, decode_url,
    decoded_frame, validate_prior
)
from shared_url_safe_probe import SafeFetchError


def data_source(n):
    entries = ["#EXTM3U"]
    for i in range(n):
        entries += [
            f'#EXTINF:-1 tvg-id="id{i}" group-title="ANA ARŞİV",Name {i}',
            f"https://example.invalid/{i}.ts?token=PRIVATE",
        ]
    return "\n".join(entries) + "\n"


def prior_for(text, shard):
    records, ordered = index_playlist(text)
    hashes = ordered[shard * SHARD_SIZE:(shard + 1) * SHARD_SIZE]
    import hashlib
    return {
        "policy": PRIOR_POLICY,
        "playlist_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "playlist_records": records,
        "unique_url_count": len(ordered),
        "shard": shard,
        "shard_size": SHARD_SIZE,
        "complete": True,
        "results": [
            {"url_sha256": digest,
             "evidence": {"status": (
                 "ONE_VIDEO_SERVICE_OBSERVED" if i % 2 else "HTTP_UNAVAILABLE")}}
            for i, (digest, _) in enumerate(hashes)
        ],
    }


def offline_probe(url):
    return {
        "status": "VIDEO_AND_AUDIO_DECODED",
        "sample_bytes": 1024,
        "decoded_video": True,
        "decoded_audio": True,
        "broadcaster_identity_verified": False,
    }


class DecodedFrameTests(unittest.TestCase):
    def test_only_local_pipe_mpegts_allowed(self):
        def invoke(command, **kwargs):
            self.assertEqual(kwargs["input"], b"ts-bytes")
            self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
            self.assertIn("-protocol_whitelist", command)
            self.assertEqual(command[command.index("-protocol_whitelist") + 1], "pipe")
            self.assertIn("pipe:0", command)
            self.assertNotIn("http:", " ".join(command))
            self.assertIn("-f", command)
            return subprocess.CompletedProcess(command, 0, b"# header\n0, 0, 0, 1, 1024, abcdef\n")
        self.assertTrue(decoded_frame(b"ts-bytes", "v", "/usr/bin/ffmpeg", runner=invoke))
        self.assertTrue(decoded_frame(b"ts-bytes", "a", "/usr/bin/ffmpeg", runner=invoke))

    def test_empty_frame_list_is_not_verification(self):
        def fake(*_a, **_kw):
            return subprocess.CompletedProcess([], 0, b"# comments only\n")
        self.assertFalse(decoded_frame(b"data", "v", "ffmpeg", runner=fake))

    def test_network_is_not_exposed_to_ffmpeg(self):
        with patch("full_playlist_av_decode.sample_transport_stream",
                   return_value=b"synthetic"), \
             patch("full_playlist_av_decode.program_table", return_value=[]), \
             patch("full_playlist_av_decode.shutil.which",
                   return_value="/usr/bin/ffmpeg"), \
             patch("full_playlist_av_decode.decoded_frame",
                   side_effect=[True, False]) as decode:
            report = decode_url("https://example.invalid/secret?token=SENSITIVE")
        self.assertEqual(report["status"], "VIDEO_ONLY_DECODED")
        self.assertFalse(report["decoded_audio"])
        self.assertEqual(decode.call_args_list[0].args[0], b"synthetic")
        self.assertNotIn("SENSITIVE", str(report))

    def test_fetch_error_is_unknown_not_dead(self):
        with patch("full_playlist_av_decode.sample_transport_stream",
                   side_effect=SafeFetchError("REDIRECT_BLOCKED")):
            report = decode_url("https://example.invalid/private")
        self.assertEqual(report["status"], "REDIRECT_BLOCKED")
        self.assertFalse(report["decoded_video"])


class FullAVBatchTests(unittest.TestCase):
    def test_bound_shard_cannot_be_stale_or_partial(self):
        text = data_source(2)
        prior = prior_for(text, 0)
        self.assertEqual(len(validate_prior(text, 0, prior)[2]), 2)
        prior["playlist_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_prior(text, 0, prior)

    def test_bad_previous_hash_is_refused(self):
        text = data_source(2)
        prior = prior_for(text, 0)
        prior["results"][0]["url_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_prior(text, 0, prior)

    def test_multiple_channel_records_one_url_one_decode(self):
        text = ("#EXTM3U\n"
                '#EXTINF:-1 group-title="YEDEKLER",One\n'
                "https://example.invalid/path.ts?token=PRIVATE\n"
                '#EXTINF:-1 group-title="ANA ARŞİV",Two\n'
                "https://example.invalid/path.ts?token=PRIVATE\n")
        prior = prior_for(text, 0)
        seen = []
        def probe(url):
            seen.append(url)
            return offline_probe(url)
        output = batch(text, 0, prior, probe=probe)
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(output["attempts"][0]["channel_records"]), 2)
        self.assertFalse(output["attempts"][0]["safe_to_remove_or_merge"])
        self.assertNotIn("PRIVATE", str(output))
        self.assertTrue(output["complete"])

    def test_consolidate_incomplete_cannot_claim_all_urls(self):
        text = data_source(3)
        reports = [batch(text, i, prior_for(text, i), probe=offline_probe)
                   for i in range(MAX_SHARDS)]
        summary = consolidate(text, reports)
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["unique_urls"], 3)
        self.assertEqual(summary["decoded_video_and_audio_urls"], 3)
        self.assertEqual(summary["attempted_urls"], 3)
        self.assertTrue(summary["no_channels_mutated"])
        self.assertFalse(summary["broadcaster_identity_verified"])
        fail = consolidate(text, reports[:-1])
        self.assertFalse(fail["complete"])
        self.assertIn("MISSING_SHARDS", fail["issues"])

    def test_fake_success_wrong_hash_is_rejected(self):
        text = data_source(1)
        reports = [batch(text, i, prior_for(text, i), probe=offline_probe)
                   for i in range(MAX_SHARDS)]
        reports[0]["attempts"][0]["url_sha256"] = "bad"
        s = consolidate(text, reports)
        self.assertFalse(s["complete"])
        self.assertEqual(s["missing_urls"], 1)

    def test_all_shards_are_bounded(self):
        text = data_source(SHARD_SIZE + 1)
        total, _ = index_playlist(text)
        self.assertEqual(total, SHARD_SIZE + 1)
        for shard, count in ((0, SHARD_SIZE), (1, 1), (35, 0)):
            output = batch(text, shard, prior_for(text, shard),
                           probe=offline_probe)
            self.assertEqual(len(output["attempts"]), count)


if __name__ == "__main__":
    unittest.main()
