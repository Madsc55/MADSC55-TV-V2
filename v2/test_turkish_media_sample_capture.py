import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from v2.turkish_media_sample_capture import capture, validate_url

class CaptureTests(unittest.TestCase):
    def test_bad_urls(self):
        for url in ("file:///tmp/secret", "http://user:pass@example.com/live", "ftp://host/live", "http://host/x#frag"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
    def test_reject_private_and_local_destinations(self):
        for url in ("http://127.0.0.1/live", "http://10.0.0.1/live", "http://192.168.1.1/live", "http://[::1]/live", "https://localhost/live", "https://server.local/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
    def test_reject_long_duration_and_timeout(self):
        with self.assertRaises(ValueError):
            capture("https://example.com/live", "/tmp/unused.mkv", seconds=13)
        with self.assertRaises(ValueError):
            capture("https://example.com/live", "/tmp/unused.mkv", timeout=18)
    def test_no_ffmpeg_is_not_success(self):
        r = capture("https://example.com/live", "/tmp/unused.mkv", which=lambda _: None)
        self.assertEqual(r["status"], "FFMPEG_UNAVAILABLE")
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"sample.mkv"
            p.write_bytes(b"existing")
            with self.assertRaises(ValueError):
                capture("https://example.com/live", p, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(p.read_bytes(), b"existing")
    def test_success_is_not_language_proof(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"sample.mkv"
            def runner(cmd, **kwargs):
                self.assertLessEqual(kwargs["timeout"], 17)
                p.write_bytes(b"sample")
                return SimpleNamespace(returncode=0)
            r = capture("https://example.com/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(r["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            self.assertFalse(r["language_verified"])
            self.assertFalse(r["asr_completed"])
            self.assertFalse(r["ocr_completed"])
    def test_failed_capture_cleans_partial_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"sample.mkv"
            def runner(cmd, **kwargs):
                p.write_bytes(b"partial")
                return SimpleNamespace(returncode=1)
            r = capture("https://example.com/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg")
            self.assertEqual(r["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())

if __name__ == "__main__":
    unittest.main()
