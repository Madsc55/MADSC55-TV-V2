#!/usr/bin/env python3
"""Offline safety and PAT/PMT acceptance for bounded untrusted-IPTV sampling."""
import json
import socket
import unittest
from unittest.mock import patch

from shared_url_safe_probe import (
    SafeFetchError, bounded_get, vetted_target, sample_transport_stream,
    program_table, inspect_url,
)
from shared_url_live_review import review


def packet(pid, section):
    payload = b"\x00" + section
    assert len(payload) <= 184
    header = bytes([0x47, 0x40 | (pid >> 8), pid & 255, 0x10])
    return header + payload + b"\xff" * (184 - len(payload))


def section(table_id, body):
    length = len(body) + 4
    return bytes([table_id, 0xB0 | (length >> 8), length & 255]) + body + bytes(4)


def stream_sample(two=True):
    entries = (
        b"\x00\x65\xe1\x00" +
        (b"\x00\xca\xe1\x01" if two else b"")
    )
    pat = section(0, b"\x00\x01\xc1\x00\x00" + entries)
    def pmt(n, video_pid, audio_pid):
        start = n.to_bytes(2, "big") + b"\xc1\x00\x00\xe1\x01\xf0\x00"
        video = b"\x1b" + bytes([0xe0 | (video_pid >> 8), video_pid & 255]) + b"\xf0\x00"
        audio = b"\x0f" + bytes([0xe0 | (audio_pid >> 8), audio_pid & 255]) + b"\xf0\x00"
        return section(2, start + video + audio)
    pmt1 = packet(256, pmt(101, 301, 401))
    pmt2 = packet(257, pmt(202, 302, 402)) if two else b""
    return packet(0, pat) + pmt1 + pmt2 + packet(0, pat)


class SampleSafetyTests(unittest.TestCase):
    def test_rejects_credentials_private_hosts_and_control_characters(self):
        for url in (
            "file:///etc/passwd", "http://127.0.0.1/live.ts",
            "https://localhost/live.ts", "https://user:pw@public.example/live",
            "http://169.254.169.254/latest/meta-data/",
            "https://public.example:12345/x", "http://public.example/\r\nx",
            "https://public.example/%0a", "http://[::1]/",
        ):
            with self.subTest(url=url), self.assertRaises(SafeFetchError):
                with patch("shared_url_safe_probe.socket.getaddrinfo",
                           return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]):
                    vetted_target(url)

    def test_fails_closed_on_mixed_dns_answers(self):
        with patch("shared_url_safe_probe.socket.getaddrinfo",
                   return_value=[
                       (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
                       (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443)),
                   ]):
            with self.assertRaisesRegex(SafeFetchError, "PRIVATE_IP"):
                vetted_target("https://public.example/stream.ts")

    def test_public_dns_target_is_pinned_to_numeric_ip(self):
        with patch("shared_url_safe_probe.socket.getaddrinfo",
                   return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]):
            result = vetted_target("https://public.example/stream.ts?token=secret")
        self.assertEqual(result, ("https", "public.example", 443, "8.8.8.8",
                                  "/stream.ts?token=secret"))

    def test_redirect_is_blocked_without_following(self):
        class Response:
            status = 302
        class Conn:
            def __init__(self, *args):
                pass
            def request(self, *args, **kwargs):
                pass
            def getresponse(self):
                return Response()
            def close(self):
                pass
        with patch("shared_url_safe_probe.vetted_target",
                   return_value=("http", "public.example", 80, "8.8.8.8", "/x")), \
             patch("shared_url_safe_probe.PinnedHTTP", Conn):
            with self.assertRaisesRegex(SafeFetchError, "REDIRECT_BLOCKED"):
                bounded_get("http://public.example/x")

    def test_hls_segments_resolve_relative_and_do_not_fetch_keys(self):
        master = "https://public.example/master.m3u8"
        variant = "https://public.example/video/index.m3u8"
        segment = "https://public.example/video/s2.ts"
        called = []
        def fake_fetch(url, limit):
            called.append(url)
            return {
                master: b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=500000\nvideo/index.m3u8\n",
                variant: b"#EXTM3U\n#EXTINF:3,\ns1.ts\n#EXTINF:3,\ns2.ts\n",
                segment: stream_sample(),
            }[url]
        self.assertEqual(sample_transport_stream(master, fake_fetch), stream_sample())
        self.assertEqual(called, [master, variant, segment])

    def test_encrypted_hls_is_blocked(self):
        def fake_fetch(url, limit):
            return b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXTINF:3,\nx.ts\n'
        with self.assertRaisesRegex(SafeFetchError, "ENCRYPTED_HLS_UNSUPPORTED"):
            sample_transport_stream("https://public.example/live.m3u8", fake_fetch)

    def test_two_programs_have_distinct_video_and_audio_pids(self):
        programs = program_table(stream_sample())
        self.assertEqual(programs, [
            {"program_number": 101, "video_pids": [301], "audio_pids": [401]},
            {"program_number": 202, "video_pids": [302], "audio_pids": [402]},
        ])
        result = inspect_url("https://public.example/mux.ts", lambda _url, _n: stream_sample())
        self.assertEqual(result["status"], "MULTIPLE_VIDEO_SERVICE_PIDS_OBSERVED")
        self.assertFalse(result["distinct_broadcasters_verified"])
        self.assertFalse(result["audio_video_decoded_verified"])

    def test_single_program_does_not_prove_absence_of_more(self):
        result = inspect_url("https://public.example/one.ts",
                             lambda _url, _n: stream_sample(False))
        self.assertEqual(result["status"], "ONE_VIDEO_SERVICE_OBSERVED")
        self.assertEqual(len(result["programs"]), 1)

    def test_report_never_contains_stream_token_or_auto_deletion(self):
        u = "https://public.example/path.ts?token=PRIVATE-SECRET"
        data = (
            "#EXTM3U\n#EXTINF:-1 tvg-id=\"same\",News 1\n" + u +
            "\n#EXTINF:-1 tvg-id=\"same\",News 2\n" + u + "\n"
        )
        output = review(data, live=True, probe=lambda url: {
            "status": "ONE_VIDEO_SERVICE_OBSERVED", "sample_bytes": 1024,
            "programs": [], "distinct_broadcasters_verified": False,
            "audio_video_decoded_verified": False
        })
        self.assertEqual(output["matched_url_groups"], 1)
        self.assertFalse(output["findings"][0]["safe_to_remove_or_merge"])
        self.assertNotIn("PRIVATE-SECRET", json.dumps(output))
        self.assertNotIn(u, json.dumps(output))


if __name__ == "__main__":
    unittest.main()
