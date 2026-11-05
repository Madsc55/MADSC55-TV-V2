#!/usr/bin/env python3
"""Grouped, no-network regression for bounded second HLS FFprobe+FFmpeg proof."""
import hashlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orphan_strong_av_probe import extended_probe

URL = "https://public.example.org/late-audio.m3u8"
DIGEST = hashlib.sha256(URL.encode()).hexdigest()


def state(status="VIDEO_ONLY"):
    return {"url_sha256": DIGEST, "status": status,
            "video": status == "VIDEO_ONLY", "audio": False,
            "decoded": False, "audio_lang_tags": []}


class StrongOrphanAVTests(unittest.TestCase):
    def test_late_audio_is_confirmed_only_after_both_real_media_commands(self):
        commands = []
        def runner(cmd, **kwargs):
            commands.append(cmd)
            if cmd[0] == "ffprobe":
                return SimpleNamespace(returncode=0, stdout=json.dumps(
                    {"streams": [{"codec_type":"video"},{"codec_type":"audio"}]}))
            return SimpleNamespace(returncode=0, stdout="")
        with patch("orphan_strong_av_probe.validate_url", return_value=True), \
             patch("orphan_strong_av_probe.public_dns", return_value=True):
            out = extended_probe((DIGEST, URL), state(), runner=runner,
                                 resolver=lambda _: True)
        self.assertTrue(out["decoded"])
        self.assertEqual(out["status"], "VIDEO_AUDIO_DECODED")
        self.assertEqual([x[0] for x in commands], ["ffprobe", "ffmpeg"])
        self.assertIn("-map", commands[1])
        self.assertNotIn("-headers", commands[1])
        self.assertNotIn("-user_agent", commands[1])

    def test_http_403_404_and_auth_are_never_retried(self):
        for status in ("PROBE_FAILED_HTTP_FORBIDDEN",
                       "PROBE_FAILED_HTTP_NOT_FOUND", "PROBE_FAILED_AUTH_REQUIRED"):
            with self.subTest(status=status):
                out = state(status)
                self.assertIs(extended_probe((DIGEST, URL), out,
                    runner=lambda *a, **kw: self.fail("No retry 403,404,401"),
                    resolver=lambda _: self.fail("No DNS on forbidden URL")), out)

    def test_missing_audio_or_decode_failure_never_claimed_working(self):
        def runner(cmd, **kw):
            if cmd[0] == "ffprobe":
                return SimpleNamespace(returncode=0,
                    stdout=json.dumps({"streams":[{"codec_type":"video"}]}))
            self.fail("No FFmpeg without both tracks")
        initial=state()
        with patch("orphan_strong_av_probe.validate_url", return_value=True):
            self.assertIs(extended_probe((DIGEST, URL), initial, runner=runner,
                            resolver=lambda _: True), initial)
        def fails(cmd, **kw):
            return SimpleNamespace(returncode=0 if cmd[0] == "ffprobe" else 1,
                 stdout=json.dumps({"streams":[{"codec_type":"video"},
                                               {"codec_type":"audio"}]}))
        with patch("orphan_strong_av_probe.validate_url", return_value=True):
            self.assertIs(extended_probe((DIGEST, URL), initial, runner=fails,
                            resolver=lambda _: True), initial)

    def test_invalid_url_sha_or_fake_initial_success_is_hard_error(self):
        with self.assertRaisesRegex(ValueError, "exact URL SHA256"):
            extended_probe(("0"*64, URL), state())
        fake = state()
        fake["url_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "first-stage"):
            extended_probe((DIGEST, URL), fake)

    def test_unsafe_dns_does_not_start_second_media_process(self):
        out = state("PROBE_UNCONFIRMED")
        self.assertIs(extended_probe((DIGEST, URL), out,
            runner=lambda *a, **kw: self.fail("Unsafe source probed"),
            resolver=lambda _: False), out)


if __name__ == "__main__":
    unittest.main()
