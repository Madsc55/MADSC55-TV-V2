"""Offline bounded capture regressions including public numeric IP literals."""
import datetime
import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from v2.turkish_media_sample_capture import MAX_BYTES, capture, validate_url

PUBLIC_URL = "https://8.8.8.8/media.mp4"
VIDEO = b"0000ftypisommedia"


def fake_connection_factory(body=VIDEO, *, status=200, content_type="video/mp4"):
    """A pinned HTTP response fixture; never accesses the network."""
    class Response:
        def __init__(self):
            self.status = status
            self.data = io.BytesIO(body)

        def getheader(self, header):
            if header.lower() == "content-type":
                return content_type
            return None

        def read(self, length):
            return self.data.read(length)

    class Connection:
        sock = None

        def __init__(self, host, port, pinned_ip, timeout):
            self.pinned_ip = pinned_ip
            if pinned_ip != "8.8.8.8":
                raise AssertionError("unexpected target")

        def request(self, method, target, headers):
            if method != "GET":
                raise AssertionError("unexpected method")

        def getresponse(self):
            return Response()

        def close(self):
            pass

    return Connection


def offline_capture(path, runner, *, connection_factory=None):
    return capture(PUBLIC_URL, path, runner=runner,
                   which=lambda _: "/usr/bin/ffmpeg",
                   connection_factory=connection_factory or fake_connection_factory())


class CaptureTests(unittest.TestCase):
    def test_bad_urls(self):
        for url in ("file:///tmp/secret",
                    "http://user:pass@example.com/live",
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
        self.assertEqual(validate_url("https://example.com/live"),
                         "https://example.com/live")

    def test_ambiguous_url_authority_and_controls_rejected(self):
        for url in (" http://8.8.8.8/live",
                    "http://8.8.8.8/live\nplaylist",
                    "http://8.8.8.8/live\tplaylist",
                    "http://8.8.8.8/with space",
                    "http://8.8.8.8\\@127.0.0.1/live",
                    "http://%38.8.8.8/live",
                    "http://8.8.8.8/path\\file"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
        self.assertEqual(validate_url("https://8.8.8.8/live?token=a%20b"),
                         "https://8.8.8.8/live?token=a%20b")

    def test_numeric_ip_ffmpeg_receives_only_local_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                self.assertEqual(cmd[cmd.index("-protocol_whitelist") + 1], "file")
                self.assertNotIn(PUBLIC_URL, cmd)
                self.assertNotIn("http", cmd)
                self.assertNotIn("https", cmd)
                self.assertEqual(cmd[cmd.index("-f") + 1], "mov")
                source = Path(cmd[cmd.index("-i") + 1])
                self.assertTrue(source.is_file())
                self.assertEqual(source.read_bytes(), VIDEO)
                Path(cmd[-1]).write_bytes(b"decoded")
                return SimpleNamespace(returncode=0)
            result = offline_capture(p, runner)
            self.assertEqual(result["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            self.assertEqual(p.read_bytes(), b"decoded")
            self.assertFalse(result["language_verified"])
            self.assertFalse(result["device_verified"])

    def test_numeric_ip_hls_private_segment_is_rejected_before_ffmpeg(self):
        hls = b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nhttp://127.0.0.1/key\n"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                raise AssertionError("FFmpeg must not be invoked on HLS")
            with self.assertRaises(ValueError):
                offline_capture(p, runner,
                                connection_factory=fake_connection_factory(body=hls))
            self.assertFalse(p.exists())

    def test_numeric_ip_redirect_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                raise AssertionError("FFmpeg must not run after redirect")
            with self.assertRaises(ValueError):
                offline_capture(p, runner,
                                connection_factory=fake_connection_factory(status=302))
            self.assertFalse(p.exists())

    def test_invalid_ports_rejected(self):
        for url in ("http://8.8.8.8:abc/live", "http://8.8.8.8:65536/live",
                    "http://8.8.8.8:0/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_symlink_created_during_capture_never_clobbers_target(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            target = Path(d) / "protected.txt"
            target.write_text("untouched")
            def runner(cmd, **kwargs):
                p.symlink_to(target)
                Path(cmd[-1]).write_bytes(b"decoded")
                return SimpleNamespace(returncode=0)
            with self.assertRaises(ValueError):
                offline_capture(p, runner)
            self.assertTrue(p.is_symlink())
            self.assertEqual(target.read_text(), "untouched")

    def test_reject_long_duration_and_timeout(self):
        with self.assertRaises(ValueError):
            capture(PUBLIC_URL, "/tmp/unused.mkv", seconds=13)
        with self.assertRaises(ValueError):
            capture(PUBLIC_URL, "/tmp/unused.mkv", timeout=18)

    def test_no_ffmpeg_is_not_success(self):
        report = capture(PUBLIC_URL, "/tmp/unused.mkv", which=lambda _: None)
        self.assertEqual(report["status"], "FFMPEG_UNAVAILABLE")

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            p.write_bytes(b"existing")
            with self.assertRaises(ValueError):
                capture(PUBLIC_URL, p, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(p.read_bytes(), b"existing")

    def test_success_is_not_language_proof(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                self.assertLessEqual(kwargs["timeout"], 17)
                Path(cmd[-1]).write_bytes(b"sample")
                return SimpleNamespace(returncode=0)
            report = offline_capture(p, runner)
            self.assertEqual(report["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            self.assertIsNotNone(datetime.datetime.fromisoformat(
                report["captured_at_utc"].replace("Z", "+00:00")).tzinfo)
            self.assertFalse(report["language_verified"])
            self.assertFalse(report["asr_completed"])
            self.assertFalse(report["ocr_completed"])

    def test_oversize_capture_is_rejected_and_removed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                with Path(cmd[-1]).open("wb") as output:
                    output.truncate(MAX_BYTES + 1)
                return SimpleNamespace(returncode=0)
            report = offline_capture(p, runner)
            self.assertEqual(report["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())

    def test_failed_capture_cleans_partial_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                Path(cmd[-1]).write_bytes(b"partial")
                return SimpleNamespace(returncode=1)
            report = offline_capture(p, runner)
            self.assertEqual(report["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())


if __name__ == "__main__":
    unittest.main()
