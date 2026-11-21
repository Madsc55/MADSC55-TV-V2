import datetime
import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from v2.turkish_media_sample_capture import MAX_BYTES, capture, validate_url


def media_connection(body=None):
    body = body if body is not None else b"\x1a\x45\xdf\xa3" + (b"\x00" * 32)
    seen = []

    class Response:
        status = 200
        def __init__(self):
            self.source = io.BytesIO(body)
        def getheader(self, name):
            return {"content-type": "video/x-matroska",
                    "content-length": str(len(body))}.get(name.lower())
        def read(self, count):
            return self.source.read(count)

    class Connection:
        sock = None
        def __init__(self, host, port, pinned_ip, timeout):
            seen.append({"host": host, "port": port, "pinned_ip": pinned_ip})
        def request(self, method, target, headers):
            seen[-1].update({"method": method, "target": target, "headers": headers})
        def getresponse(self):
            return Response()
        def close(self):
            seen[-1]["closed"] = True

    return Connection, seen


class CaptureTests(unittest.TestCase):
    def test_bad_urls(self):
        for url in ("file:///tmp/secret", "http://user:pass@example.com/live",
                    "ftp://host/live", "http://host/x#frag"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_reject_private_and_local_destinations(self):
        for url in ("http://127.0.0.1/live", "http://10.0.0.1/live",
                    "http://192.168.1.1/live", "http://[::1]/live",
                    "https://localhost/live", "https://server.local/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_dns_name_syntax_is_safe_before_pinned_network_resolution(self):
        self.assertEqual(validate_url("https://example.com/live"), "https://example.com/live")

    def test_ambiguous_url_authority_and_controls_rejected(self):
        for url in (" http://8.8.8.8/live", "http://8.8.8.8/live\nplaylist",
                    "http://8.8.8.8/live\tplaylist", "http://8.8.8.8/with space",
                    "http://8.8.8.8\\@127.0.0.1/live", "http://%38.8.8.8/live",
                    "http://8.8.8.8/path\\file"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
        self.assertEqual(validate_url("https://8.8.8.8/live?token=a%20b"),
                         "https://8.8.8.8/live?token=a%20b")

    def test_ffmpeg_receives_only_local_media_and_file_protocol(self):
        factory, seen = media_connection()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                self.assertEqual(cmd[cmd.index("-protocol_whitelist") + 1], "file")
                self.assertEqual(cmd[cmd.index("-f") + 1], "matroska")
                source = Path(cmd[cmd.index("-i") + 1])
                self.assertTrue(source.is_file())
                self.assertNotIn("https://8.8.8.8/live", cmd)
                p.write_bytes(b"decoded-sample")
                return SimpleNamespace(returncode=0)
            report = capture("https://8.8.8.8/live", p, runner=runner,
                             which=lambda _: "/usr/bin/ffmpeg", connection_factory=factory)
            self.assertEqual(report["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            self.assertEqual(seen[0]["pinned_ip"], "8.8.8.8")
            self.assertEqual(seen[0]["headers"]["Host"], "8.8.8.8")
            self.assertFalse(report["language_verified"])
            self.assertFalse(report["device_verified"])

    def test_invalid_ports_rejected(self):
        for url in ("http://8.8.8.8:abc/live", "http://8.8.8.8:65536/live",
                    "http://8.8.8.8:0/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_destination_symlink_race_never_overwrites_target(self):
        factory, _ = media_connection()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            target = Path(d) / "protected.txt"
            target.write_text("untouched")
            def runner(cmd, **kwargs):
                Path(cmd[-1]).write_bytes(b"decoded-sample")
                p.symlink_to(target)
                return SimpleNamespace(returncode=0)
            with self.assertRaises(ValueError):
                capture("http://8.8.8.8/live", p, runner=runner,
                        which=lambda _: "/usr/bin/ffmpeg", connection_factory=factory)
            self.assertTrue(p.is_symlink())
            self.assertEqual(target.read_text(), "untouched")

    def test_reject_long_duration_and_timeout(self):
        with self.assertRaises(ValueError):
            capture("http://8.8.8.8/live", "/tmp/unused.mkv", seconds=13)
        with self.assertRaises(ValueError):
            capture("http://8.8.8.8/live", "/tmp/unused.mkv", timeout=18)

    def test_no_ffmpeg_is_not_success(self):
        r = capture("http://8.8.8.8/live", "/tmp/unused.mkv", which=lambda _: None)
        self.assertEqual(r["status"], "FFMPEG_UNAVAILABLE")

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            p.write_bytes(b"existing")
            with self.assertRaises(ValueError):
                capture("http://8.8.8.8/live", p, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(p.read_bytes(), b"existing")

    def test_success_is_not_language_proof(self):
        factory, _ = media_connection()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                self.assertLessEqual(kwargs["timeout"], 17)
                Path(cmd[-1]).write_bytes(b"decoded-sample")
                return SimpleNamespace(returncode=0)
            r = capture("http://8.8.8.8/live", p, runner=runner,
                        which=lambda _: "/usr/bin/ffmpeg", connection_factory=factory)
            self.assertEqual(r["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            stamp = datetime.datetime.fromisoformat(r["captured_at_utc"].replace("Z", "+00:00"))
            self.assertIsNotNone(stamp.tzinfo)
            self.assertFalse(r["language_verified"])
            self.assertFalse(r["asr_completed"])
            self.assertFalse(r["ocr_completed"])

    def test_oversize_decoded_output_is_rejected(self):
        factory, _ = media_connection()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                with Path(cmd[-1]).open("wb") as output:
                    output.truncate(MAX_BYTES + 1)
                return SimpleNamespace(returncode=0)
            r = capture("http://8.8.8.8/live", p, runner=runner,
                        which=lambda _: "/usr/bin/ffmpeg", connection_factory=factory)
            self.assertEqual(r["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())

    def test_failed_decode_cleans_private_staging(self):
        factory, _ = media_connection()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                Path(cmd[-1]).write_bytes(b"partial")
                return SimpleNamespace(returncode=1)
            r = capture("http://8.8.8.8/live", p, runner=runner,
                        which=lambda _: "/usr/bin/ffmpeg", connection_factory=factory)
            self.assertEqual(r["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())


if __name__ == "__main__":
    unittest.main()
