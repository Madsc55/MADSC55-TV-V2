import datetime
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from v2.turkish_media_sample_capture import MAX_BYTES, capture, validate_url

class CaptureTests(unittest.TestCase):
    def test_bad_urls(self):
        for url in ("file:///tmp/secret", "http://user:pass@example.com/live", "ftp://host/live", "http://host/x#frag"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
    def test_reject_private_and_local_destinations(self):
        for url in ("http://127.0.0.1/live", "http://10.0.0.1/live", "http://192.168.1.1/live", "http://[::1]/live", "https://localhost/live", "https://server.local/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
    def test_dns_names_rejected_to_prevent_rebinding(self):
        with self.assertRaises(ValueError):
            validate_url("https://example.com/live")
    def test_invalid_ports_rejected(self):
        for url in ("http://8.8.8.8:abc/live", "http://8.8.8.8:65536/live", "http://8.8.8.8:0/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_symlink_created_during_capture_removed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"sample.mkv"
            target = Path(d)/"protected.txt"
            target.write_text("untouched")
            def runner(cmd, **kwargs):
                p.symlink_to(target)
                return SimpleNamespace(returncode=0)
            with self.assertRaises(ValueError):
                capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg")
            self.assertFalse(p.is_symlink())
            self.assertEqual(target.read_text(), "untouched")

    def test_redirects_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"sample.mkv"
            def runner(cmd, **kwargs):
                self.assertEqual(cmd[cmd.index("-max_redirect")+1], "0")
                self.assertEqual(cmd[cmd.index("-fs")+1], str(MAX_BYTES))
                p.write_bytes(b"sample")
                return SimpleNamespace(returncode=0)
            capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg")
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
            p = Path(d)/"sample.mkv"
            p.write_bytes(b"existing")
            with self.assertRaises(ValueError):
                capture("http://8.8.8.8/live", p, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(p.read_bytes(), b"existing")
    def test_success_is_not_language_proof(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"sample.mkv"
            def runner(cmd, **kwargs):
                self.assertLessEqual(kwargs["timeout"], 17)
                p.write_bytes(b"sample")
                return SimpleNamespace(returncode=0)
            r = capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(r["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            stamp = datetime.datetime.fromisoformat(r["captured_at_utc"].replace("Z", "+00:00"))
            self.assertIsNotNone(stamp.tzinfo)
            self.assertFalse(r["language_verified"])
            self.assertFalse(r["asr_completed"])
            self.assertFalse(r["ocr_completed"])
    def test_oversize_capture_is_rejected_and_removed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"sample.mkv"
            def runner(cmd, **kwargs):
                with p.open("wb") as output:
                    output.truncate(MAX_BYTES + 1)
                return SimpleNamespace(returncode=0)
            r = capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(r["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())

    def test_failed_capture_cleans_partial_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"sample.mkv"
            def runner(cmd, **kwargs):
                p.write_bytes(b"partial")
                return SimpleNamespace(returncode=1)
            r = capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(r["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())

if __name__ == "__main__":
    unittest.main()
