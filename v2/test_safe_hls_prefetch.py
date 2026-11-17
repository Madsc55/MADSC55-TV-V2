import socket
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from v2.safe_hls_prefetch import (
    UnsafeMediaSource, public_endpoints, fetch_pinned, prefetch_hls,
    subtitle_observations,
    MAX_SEGMENT_BYTES, MAX_MANIFEST_BYTES
)

class SafeHLSPrefetchTests(unittest.TestCase):
    def test_mixed_and_private_dns_fail_closed(self):
        def answer(ip):
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            return (family, socket.SOCK_STREAM, 6, "", (ip, 443))
        with patch("v2.safe_hls_prefetch.socket.getaddrinfo",
                   return_value=[answer("8.8.8.8"), answer("127.0.0.1")]):
            with self.assertRaises(UnsafeMediaSource):
                public_endpoints("https://example.org/live.m3u8")
        with patch("v2.safe_hls_prefetch.socket.getaddrinfo",
                   return_value=[answer("8.8.8.8")]):
            self.assertEqual(public_endpoints("https://example.org/live.m3u8")[2],
                             ["8.8.8.8"])

    def test_missing_dns_or_local_url_fails(self):
        with patch("v2.safe_hls_prefetch.socket.getaddrinfo",
                   side_effect=socket.gaierror("No DNS")):
            with self.assertRaises(UnsafeMediaSource):
                public_endpoints("https://example.org/live.m3u8")
        with self.assertRaises(UnsafeMediaSource):
            public_endpoints("http://169.254.169.254/metadata")

    def test_local_manifest_contains_no_raw_network_url(self):
        master = b"#EXTM3U\n#EXT-X-TARGETDURATION:5\n#EXTINF:5,\nhttps://media.example.org/a.ts\n#EXTINF:5,\n/b.ts\n"
        def getter(url, limit):
            return master if url.endswith(".m3u8") else b"TEST-TS-SEGMENT"
        with TemporaryDirectory() as tmp:
            result = prefetch_hls("https://example.org/live.m3u8",
                                  tmp, seconds=8, getter=getter)
            raw = result.read_text(encoding="utf-8")
            self.assertNotIn("https://", raw)
            self.assertNotIn("http://", raw)
            self.assertNotIn("/b.ts", raw)
            self.assertEqual(len(list(Path(tmp).glob("segment-*.ts"))), 2)
            self.assertIn("#EXT-X-ENDLIST", raw)

    def test_unsupported_encryption_map_and_byterange_rejected(self):
        forbidden = (
            '#EXT-X-KEY:METHOD=AES-128,URI="https://example.org/key"',
            "#EXT-X-BYTERANGE:1024@0",
            '#EXT-X-MAP:URI="init.mp4"',
            '#EXT-X-PART:DURATION=1,URI="part.ts"',
        )
        for line in forbidden:
            manifest = ("#EXTM3U\n" + line + "\n#EXTINF:5,\nseg.ts\n").encode()
            with TemporaryDirectory() as tmp, self.subTest(line=line):
                with self.assertRaises(UnsafeMediaSource):
                    prefetch_hls("https://example.org/live.m3u8",
                                 tmp, getter=lambda *_: manifest)

    def test_redirect_rejected_without_following_location(self):
        with patch("v2.safe_hls_prefetch.public_endpoints",
                   return_value=(urlsplit("https://example.org/live.m3u8"),
                                 443, ["8.8.8.8"])):
            with patch("v2.safe_hls_prefetch.ssl.create_default_context"):
                with patch("v2.safe_hls_prefetch.http.client.HTTPSConnection") as creator:
                    conn = creator.return_value
                    conn.getresponse.return_value.status = 302
                    with self.assertRaises(UnsafeMediaSource):
                        fetch_pinned("https://example.org/live.m3u8", MAX_MANIFEST_BYTES)
                    self.assertEqual(conn.request.call_count, 1)
                    conn.close.assert_called_once()

    def test_nested_private_segment_rejected_at_fetch_boundary(self):
        manifest = b"#EXTM3U\n#EXTINF:5,\nhttp://127.0.0.1/a.ts\n"
        def getter(url, limit):
            if url.endswith(".m3u8"):
                return manifest
            public_endpoints(url)
            return b"TEST-SEGMENT"
        with TemporaryDirectory() as tmp:
            with self.assertRaises(UnsafeMediaSource):
                prefetch_hls("https://example.org/live.m3u8", tmp, getter=getter)

    def test_existing_local_output_cannot_be_overwritten(self):
        manifest = b"#EXTM3U\n#EXTINF:6,\nseg.ts\n"
        getter = lambda u, limit: manifest if u.endswith(".m3u8") else b"SEGMENT"
        with TemporaryDirectory() as tmp:
            prefetch_hls("https://example.org/live.m3u8", tmp, getter=getter)
            with self.assertRaises(FileExistsError):
                prefetch_hls("https://example.org/live.m3u8", tmp, getter=getter)

    def test_turkish_webvtt_track_is_review_hint_only(self):
        master = (b'#EXTM3U\n#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="sub",'
                  b'LANGUAGE="tr",URI="tur.m3u8"\n'
                  b'#EXT-X-STREAM-INF:BANDWIDTH=1000000,SUBTITLES="sub"\nvideo.m3u8\n')
        tracks = b'#EXTM3U\n#EXTINF:5,\npart.vtt\n'
        cues = b'WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nT\xc3\xbcrkiye haberleri\n'
        def get(url, limit):
            if url.endswith("live.m3u8"): return master
            if url.endswith("tur.m3u8"): return tracks
            if url.endswith("part.vtt"): return cues
            raise AssertionError("Unexpected network URL")
        result = subtitle_observations("https://example.org/live.m3u8", getter=get)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["kind"], "SUBTITLE")
        self.assertEqual(result[0]["language_tag"], "tr")
        self.assertIn("Türkiye", result[0]["text"])

    def test_private_webvtt_track_is_rejected_before_media_download(self):
        master = (b'#EXTM3U\n#EXT-X-MEDIA:TYPE=SUBTITLES,'
                  b'LANGUAGE="tr",URI="http://127.0.0.1/sub.m3u8"\n')
        def get(url, limit):
            if url == "https://example.org/live.m3u8": return master
            public_endpoints(url)
            raise AssertionError("Private URL must not be fetched")
        with self.assertRaises(UnsafeMediaSource):
            subtitle_observations("https://example.org/live.m3u8", getter=get)

    def test_webvtt_requires_cue_text_not_header_only(self):
        master = (b'#EXTM3U\n#EXT-X-MEDIA:TYPE=SUBTITLES,'
                  b'LANGUAGE="tr",URI="subs.m3u8"\n')
        track = b'#EXTM3U\n#EXTINF:5,\nseg.vtt\n'
        def get(url, limit):
            if url.endswith("live.m3u8"): return master
            if url.endswith("subs.m3u8"): return track
            if url.endswith("seg.vtt"): return b"WEBVTT\n"
            raise AssertionError("Unexpected URL")
        self.assertEqual(subtitle_observations("https://example.org/live.m3u8",
                                                getter=get), [])

    def test_unfetched_iframe_metadata_cannot_trigger_private_fetch(self):
        master = (b'#EXTM3U\n'
                  b'#EXT-X-I-FRAME-STREAM-INF:BANDWIDTH=500000,'
                  b'URI="http://127.0.0.1/iframe.m3u8"\n'
                  b'#EXT-X-STREAM-INF:BANDWIDTH=1000000\nvideo.m3u8\n')
        variant = b'#EXTM3U\n#EXTINF:6,\nsegment.ts\n'
        requested=[]
        def get(url, limit):
            requested.append(url)
            if url.endswith("master.m3u8"): return master
            if url.endswith("video.m3u8"): return variant
            if url.endswith("segment.ts"): return b"LOCAL_SEGMENT"
            raise AssertionError("Unexpected remote URL requested")
        with TemporaryDirectory() as tmp:
            local=prefetch_hls("https://example.org/master.m3u8",
                               tmp, seconds=5, getter=get)
            self.assertTrue(local.exists())
        self.assertEqual(len(requested), 3)
        self.assertFalse(any("127.0.0.1" in item for item in requested))

    def test_bad_or_oversized_segment_fails_closed(self):
        manifest = b"#EXTM3U\n#EXTINF:6,\nseg.ts\n"
        def getter(url, limit):
            return manifest if url.endswith(".m3u8") else b"x" * (MAX_SEGMENT_BYTES + 1)
        with TemporaryDirectory() as tmp:
            with self.assertRaises(UnsafeMediaSource):
                prefetch_hls("https://example.org/live.m3u8", tmp, getter=getter)

if __name__ == "__main__":
    unittest.main()
