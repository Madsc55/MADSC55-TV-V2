#!/usr/bin/env python3
"""Offline HLS MPEG-TS egress-safety tests: NO actual network or media scanning."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from v2.turkish_hls_safe_segments import (
    MAX_MANIFEST_BYTES, MAX_SEGMENTS, download_hls_ts_bounded,
    fetch_hls_manifest_bounded, parse_hls_media_playlist,
)
from v2.turkish_media_sample_capture import capture

ROOT_URL = "https://8.8.8.8/live/media.m3u8"
TS = (b"\x47" + b"\x00" * 187) * 3
VALID = (b"#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n"
         b"#EXT-X-MEDIA-SEQUENCE:1\n#EXTINF:4.0,\nseg1.ts\n"
         b"#EXTINF:4.0,\nseg2.ts\n#EXT-X-ENDLIST\n")


def fixture_connection_factory(manifest=VALID, segment=TS, *, response_status=200,
                               segment_status=200, segment_type="video/mp2t"):
    calls = []

    class Response:
        def __init__(self, payload, status, kind):
            self.source = io.BytesIO(payload)
            self.status = status
            self.headers = {"content-type": kind, "content-length": str(len(payload))}

        def read(self, length):
            return self.source.read(length)

        def getheader(self, name):
            return self.headers.get(name.lower())

    class Connection:
        sock = None

        def __init__(self, host, port, pinned_ip, timeout):
            self.host = host
            self.port = port
            self.pinned_ip = pinned_ip
            self.timeout = timeout
            self.target = None

        def request(self, method, target, headers):
            assert method == "GET"
            self.target = target
            calls.append((self.host, self.port, self.pinned_ip, target, headers))

        def getresponse(self):
            if self.target.startswith("/live/media.m3u8"):
                return Response(manifest, response_status, "application/vnd.apple.mpegurl")
            return Response(segment, segment_status, segment_type)

        def close(self):
            pass

    return Connection, calls


class HLSPlanTests(unittest.TestCase):
    def test_valid_short_playlist_has_two_same_origin_ts_segments(self):
        urls = parse_hls_media_playlist(VALID, ROOT_URL)
        self.assertEqual(urls, (
            "https://8.8.8.8/live/seg1.ts",
            "https://8.8.8.8/live/seg2.ts",
        ))

    def test_negative_manifest_fixtures_fail_closed_before_segments(self):
        cases = {
            "encryption": b'#EXT-X-KEY:METHOD=AES-128,URI="http://127.0.0.1/key"\n',
            "master": b"#EXT-X-STREAM-INF:BANDWIDTH=10000\n",
            "init_map": b'#EXT-X-MAP:URI="http://127.0.0.1/init"\n',
            "byterange": b"#EXT-X-BYTERANGE:500@0\n",
            "discontinuity": b"#EXT-X-DISCONTINUITY\n",
            "foreign_url": b"#EXTINF:4,\nhttps://example.com/seg.ts\n",
            "private_url": b"#EXTINF:4,\nhttp://127.0.0.1/seg.ts\n",
            "protocol_relative": b"#EXTINF:4,\n//127.0.0.1/seg.ts\n",
            "parent_escape": b"#EXTINF:4,\n../secret.ts\n",
            "encoded_escape": b"#EXTINF:4,\n%2e%2e/secret.ts\n",
            "nested_playlist": b"#EXTINF:4,\nsecond.m3u8\n",
            "unsupported_mp4": b"#EXTINF:4,\nvideo.mp4\n",
            "newline_in_url": b"#EXTINF:4,\nsegment\x00.ts\n",
            "extra_extension": b"#EXTINF:4,\nsegment.ts.m3u8\n",
            "unknown_tag": b"#EXT-X-DEFINE:NAME=evil,VALUE=1\n",
        }
        prefix = b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n"
        for name, item in cases.items():
            if b"#EXTINF:" in item:
                raw = prefix + item + b"#EXT-X-ENDLIST\n"
            else:
                raw = prefix + item + b"#EXTINF:4,\nseg.ts\n#EXT-X-ENDLIST\n"
            with self.subTest(name=name), self.assertRaises(ValueError):
                parse_hls_media_playlist(raw, ROOT_URL)

    def test_expiration_and_manifest_grammar_must_be_consistent(self):
        for raw in (
            b"#EXTM3U\n#EXTINF:4,\nseg.ts\n",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:4,\n",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:4,\nseg.ts\n"
            b"#EXT-X-ENDLIST\n#EXTINF:2,\nmore.ts\n",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:NaN,\nseg.ts\n",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:0,\nseg.ts\n",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:31,\nseg.ts\n",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:4,\nseg.ts\n"
            b"#EXTINF:4,\nseg.ts\n",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n"
            + b"#EXTINF:4,\nseg.ts\n" * (MAX_SEGMENTS + 1),
            b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:4,\nseg.ts\n"
            + b"x" * MAX_MANIFEST_BYTES,
        ):
            with self.subTest(raw=raw[:90]), self.assertRaises(ValueError):
                parse_hls_media_playlist(raw, ROOT_URL)

    def test_url_constraints_are_strict_even_for_top_level_manifest(self):
        with self.assertRaises(ValueError):
            parse_hls_media_playlist(VALID, "http://127.0.0.1/live/media.m3u8")
        with self.assertRaises(ValueError):
            parse_hls_media_playlist(VALID, "https://8.8.8.8/master.mpd")


class HLSDownloaderTests(unittest.TestCase):
    def test_success_outputs_private_local_ts_only(self):
        factory, calls = fixture_connection_factory()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "combined.ts"
            receipt = download_hls_ts_bounded(ROOT_URL, output, connection_factory=factory)
            self.assertEqual(output.read_bytes(), TS + TS)
            self.assertEqual(receipt["input_format"], "mpegts")
            self.assertEqual(receipt["bytes"], 2 * len(TS))
            self.assertEqual(receipt["segment_count"], 2)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertEqual([row[3] for row in calls],
                         ["/live/media.m3u8", "/live/seg1.ts", "/live/seg2.ts"])
        self.assertTrue(all(row[2] == "8.8.8.8" for row in calls))

    def test_unsafe_segment_cannot_trigger_even_first_segment_fetch(self):
        manifest = (b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n"
                    b'#EXT-X-KEY:METHOD=AES-128,URI="http://127.0.0.1/key"\n'
                    b"#EXTINF:4,\nseg.ts\n")
        factory, calls = fixture_connection_factory(manifest=manifest)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "unused.ts"
            with self.assertRaises(ValueError):
                download_hls_ts_bounded(ROOT_URL, output, connection_factory=factory)
            self.assertFalse(output.exists())
        self.assertEqual(len(calls), 1)  # only the allowed manifest request

    def test_manifest_redirect_never_follows_location(self):
        factory, calls = fixture_connection_factory(response_status=302)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                download_hls_ts_bounded(ROOT_URL, Path(directory) / "unused.ts",
                                        connection_factory=factory)
        self.assertEqual(len(calls), 1)

    def test_segment_redirect_and_content_type_fail_closed(self):
        for code, kind in ((302, "video/mp2t"), (200, "text/html")):
            factory, calls = fixture_connection_factory(
                segment_status=code, segment_type=kind)
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "unused.ts"
                with self.subTest(code=code, kind=kind), self.assertRaises(ValueError):
                    download_hls_ts_bounded(ROOT_URL, output, connection_factory=factory)
                self.assertFalse(output.exists())
            self.assertEqual(len(calls), 2)

    def test_combined_byte_budget_and_no_overwrite(self):
        factory, calls = fixture_connection_factory()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "unused.ts"
            with self.assertRaises(ValueError):
                download_hls_ts_bounded(ROOT_URL, output, connection_factory=factory,
                                        max_bytes=len(TS))
            self.assertFalse(output.exists())
            output.write_bytes(b"SAFE")
            with self.assertRaises(ValueError):
                download_hls_ts_bounded(ROOT_URL, output, connection_factory=factory)
            self.assertEqual(output.read_bytes(), b"SAFE")

    def test_manifest_body_limit(self):
        factory, calls = fixture_connection_factory(manifest=VALID + b"x" * MAX_MANIFEST_BYTES)
        with self.assertRaises(ValueError):
            fetch_hls_manifest_bounded(ROOT_URL, connection_factory=factory)
        self.assertEqual(len(calls), 1)

    def test_opt_in_capture_passes_only_local_ts_to_ffmpeg(self):
        factory, calls = fixture_connection_factory()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "sample.mkv"

            def runner(cmd, **kwargs):
                self.assertEqual(cmd[cmd.index("-protocol_whitelist") + 1], "file")
                self.assertEqual(cmd[cmd.index("-f") + 1], "mpegts")
                self.assertNotIn(ROOT_URL, cmd)
                self.assertNotIn("https", cmd)
                local = Path(cmd[cmd.index("-i") + 1])
                self.assertEqual(local.read_bytes(), TS + TS)
                Path(cmd[-1]).write_bytes(b"offline-mkv-fixture")
                return SimpleNamespace(returncode=0)

            result = capture(ROOT_URL, target, which=lambda _: "/usr/bin/ffmpeg",
                             runner=runner, connection_factory=factory, allow_hls_ts=True)
            self.assertEqual(result["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            self.assertFalse(result["language_verified"])
            self.assertFalse(result["device_verified"])
            self.assertFalse(result["asr_completed"])
            self.assertFalse(result["ocr_completed"])
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(calls), 3)

    def test_default_capture_refuses_hls(self):
        factory, calls = fixture_connection_factory()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sample.mkv"
            with self.assertRaises(ValueError):
                capture(ROOT_URL, output, which=lambda _: "/usr/bin/ffmpeg",
                        runner=lambda *args, **kwargs: self.fail("No ffmpeg"),
                        connection_factory=factory)
            self.assertFalse(output.exists())
        self.assertEqual(calls, [])

    def test_invalid_hls_bool_cannot_enable_network(self):
        factory, calls = fixture_connection_factory()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                capture(ROOT_URL, Path(directory) / "sample.mkv",
                        allow_hls_ts="true", connection_factory=factory)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
