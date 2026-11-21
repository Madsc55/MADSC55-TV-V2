#!/usr/bin/env python3
"""Pinned-DNS safety regressions. No external network or live stream scans."""
import io
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from v2.turkish_safe_dns_capture import (
    MAX_REMOTE_BYTES, _PinnedHTTPS, download_bounded, parse_url, resolve_public)
from v2.turkish_media_sample_capture import capture


def public_dns(host, port, *, type):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]


def mixed_dns(host, port, *, type):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]


def factory_for(body=b"0000ftypisommedia", status=200, content_type="video/mp4",
                extra_headers=None):
    seen = []
    headers = {"content-type": content_type, **(extra_headers or {})}

    class Response:
        def __init__(self):
            self.status = status
            self.source = io.BytesIO(body)

        def getheader(self, name):
            return headers.get(name.lower())

        def read(self, count):
            return self.source.read(count)

    class Connection:
        sock = None

        def __init__(self, host, port, pinned_ip, timeout):
            seen.append({"host": host, "port": port,
                         "pinned_ip": pinned_ip, "timeout": timeout})

        def request(self, method, target, headers):
            seen[-1].update({"method": method, "target": target,
                             "headers": headers})

        def getresponse(self):
            return Response()

        def close(self):
            seen[-1]["closed"] = True

    return Connection, seen


class URLTests(unittest.TestCase):
    def test_public_dns_and_ipv4_are_accepted_without_network(self):
        self.assertEqual(parse_url("https://media.example.com/a.mp4?tag=1")[1:3],
                         ("media.example.com", 443))
        self.assertIsNone(parse_url("https://media.example.com/a.mp4")[4])
        self.assertEqual(parse_url("http://8.8.8.8/a.ts")[4].compressed,
                         "8.8.8.8")

    def test_private_ip_urls_and_hostname_masquerades_rejected(self):
        for url in (
            "http://127.0.0.1/x", "http://10.0.0.1/a",
            "http://224.0.0.1/live", "http://[ff05::1]/live",
            "http://169.254.169.254/latest", "http://[::1]/x",
            "https://internal.local/live", "https://localhost/live",
            "https://user:pass@example.com/x", "https://example.com/a#frag",
            "http://example.com:0/x", "http://bad_host.example.com/live",
            "https://example.com/master.m3u8", "https://example.com/dash.mpd",
            "https://example.com/a\r\nHeader: injected",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_url(url)

    def test_all_dns_answers_must_be_public(self):
        self.assertEqual(resolve_public("media.example.com", resolver=public_dns), ("8.8.8.8",))
        with self.assertRaises(ValueError):
            resolve_public("media.example.com", resolver=mixed_dns)
        with self.assertRaises(ValueError):
            resolve_public(
                "media.example.com",
                resolver=lambda host, port, *, type: [
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("224.0.0.1", 0))
                ])
        with self.assertRaises(ValueError):
            resolve_public("media.example.com",
                           resolver=lambda host, port, *, type: [])


class DownloadTests(unittest.TestCase):
    def test_pins_ip_without_repeated_resolve_or_redirects(self):
        counts = {"resolves": 0}
        def resolver(*args, **kwargs):
            counts["resolves"] += 1
            return public_dns(*args, **kwargs)
        factory, seen = factory_for()
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "source.bin"
            result = download_bounded("https://media.example.com/video.mp4?x=1",
                                      target, resolver=resolver,
                                      connection_factory=factory)
            self.assertEqual(target.read_bytes(), b"0000ftypisommedia")
            self.assertEqual(result["bytes"], 17)
        self.assertEqual(counts["resolves"], 1)
        self.assertEqual(seen[0]["pinned_ip"], "8.8.8.8")
        self.assertEqual(seen[0]["host"], "media.example.com")
        self.assertEqual(seen[0]["target"], "/video.mp4?x=1")
        self.assertEqual(seen[0]["headers"]["Host"], "media.example.com")
        self.assertTrue(seen[0]["closed"])

    def test_tls_pinned_ip_preserves_original_hostname_for_sni(self):
        conn = _PinnedHTTPS("media.example.com", 443, "8.8.8.8", 4)
        raw_socket = object()
        wrapped_socket = object()
        with patch("v2.turkish_safe_dns_capture.socket.create_connection",
                   return_value=raw_socket) as create, patch.object(
                       conn._context, "wrap_socket", return_value=wrapped_socket) as wrap:
            conn.connect()
            create.assert_called_once_with(("8.8.8.8", 443), 4)
            wrap.assert_called_once_with(raw_socket,
                                         server_hostname="media.example.com")
            self.assertIs(conn.sock, wrapped_socket)

    def test_tls_handshake_failure_closes_pinned_socket(self):
        conn = _PinnedHTTPS("media.example.com", 443, "8.8.8.8", 4)
        from unittest.mock import Mock
        raw_socket = Mock()
        with patch("v2.turkish_safe_dns_capture.socket.create_connection",
                   return_value=raw_socket), patch.object(
                       conn._context, "wrap_socket", side_effect=OSError("TLS failed")):
            with self.assertRaises(OSError):
                conn.connect()
        raw_socket.close.assert_called_once_with()

    def test_private_dns_is_rejected_before_connection_factory(self):
        factory, seen = factory_for()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                download_bounded("https://media.example.com/file.mp4",
                                 Path(d) / "source.bin", resolver=mixed_dns,
                                 connection_factory=factory)
        self.assertFalse(seen)

    def test_redirect_and_html_are_denied_and_cleaned(self):
        for status, content_type in [(302, "video/mp4"), (200, "text/html"),
                                     (200, "application/vnd.apple.mpegurl")]:
            factory, _ = factory_for(status=status, content_type=content_type)
            with tempfile.TemporaryDirectory() as d:
                target = Path(d) / "source.bin"
                with self.subTest(status=status, content_type=content_type):
                    with self.assertRaises(ValueError):
                        download_bounded("https://media.example.com/video",
                                         target, resolver=public_dns,
                                         connection_factory=factory)
                    self.assertFalse(target.exists())

    def test_hls_body_detected_and_rejected_without_segment_fetch(self):
        factory, seen = factory_for(
            body=b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nhttp://10.0.0.1/key\n")
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "source.bin"
            with self.assertRaises(ValueError):
                download_bounded("https://media.example.com/watch",
                                 target, resolver=public_dns,
                                 connection_factory=factory)
            self.assertFalse(target.exists())
        self.assertEqual(len(seen), 1)

    def test_ffconcat_local_file_reference_is_denied_before_ffmpeg(self):
        factory, _ = factory_for(
            body=b"ffconcat version 1.0\\nfile /etc/passwd\\n",
            content_type="video/mp4")
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "source.bin"
            with self.assertRaises(ValueError):
                download_bounded("https://media.example.com/watch",
                                 target, resolver=public_dns,
                                 connection_factory=factory)
            self.assertFalse(target.exists())

    def test_download_exceeding_limit_fails_closed(self):
        factory, _ = factory_for(body=b"x" * (MAX_REMOTE_BYTES + 1))
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "source.bin"
            with self.assertRaises(ValueError):
                download_bounded("https://media.example.com/watch",
                                 target, resolver=public_dns,
                                 connection_factory=factory)
            self.assertFalse(target.exists())


class CaptureTests(unittest.TestCase):
    def test_domain_capture_uses_only_local_media_in_ffmpeg(self):
        factory, seen = factory_for()
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                self.assertIn("-protocol_whitelist", cmd)
                self.assertEqual(cmd[cmd.index("-protocol_whitelist") + 1], "file")
                self.assertNotIn("https://media.example.com/media.mp4", cmd)
                self.assertEqual(cmd[cmd.index("-f") + 1], "mov")
                source = Path(cmd[cmd.index("-i") + 1])
                self.assertEqual(source.read_bytes(), b"0000ftypisommedia")
                Path(cmd[-1]).write_bytes(b"decoded-mkv")
                return SimpleNamespace(returncode=0)
            report = capture("https://media.example.com/media.mp4",
                             output, which=lambda _: "/usr/bin/ffmpeg",
                             runner=runner, resolver=public_dns,
                             connection_factory=factory)
            self.assertEqual(output.read_bytes(), b"decoded-mkv")
            self.assertEqual(report["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            self.assertEqual(report["dns_public_answers"], 1)
            self.assertFalse(report["language_verified"])
            self.assertFalse(report["device_verified"])
            self.assertEqual(seen[0]["pinned_ip"], "8.8.8.8")

    def test_domain_capture_never_overwrites_destination_created_during_decode(self):
        factory, _ = factory_for()
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                Path(cmd[-1]).write_bytes(b"decoded-mkv")
                output.write_bytes(b"already-here")
                return SimpleNamespace(returncode=0)
            with self.assertRaises(ValueError):
                capture("https://media.example.com/media.mp4",
                        output, runner=runner, which=lambda _: "/usr/bin/ffmpeg",
                        resolver=public_dns, connection_factory=factory)
            self.assertEqual(output.read_bytes(), b"already-here")


if __name__ == "__main__":
    unittest.main()
