import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from v2.turkish_local_media_probe import probe_local_sample

class LocalProbeTests(unittest.TestCase):
    def test_turkish_subtitle_track_is_not_verified(self):
        with tempfile.TemporaryDirectory() as d:
            sample = Path(d) / "sample.mkv"
            sample.write_bytes(b"sample")
            def runner(command, **kwargs):
                self.assertEqual(kwargs["timeout"], 10)
                self.assertNotIn("http", " ".join(command))
                return SimpleNamespace(returncode=0, stdout=json.dumps({"streams": [
                    {"index": 2, "codec_type": "subtitle", "tags": {"language": "tur"}}]}).encode())
            report = probe_local_sample(sample, runner=runner, which=lambda _: "/usr/bin/ffprobe")
            self.assertEqual(report["turkish_subtitle_track_candidates"], 1)
            self.assertFalse(report["review_approved"])
            self.assertFalse(report["playlist_modified"])

    def test_missing_ffprobe_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            sample = Path(d) / "sample.mkv"
            sample.write_bytes(b"sample")
            self.assertEqual(probe_local_sample(sample, which=lambda _: None)["status"], "FFPROBE_UNAVAILABLE")

    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            original = Path(d) / "real.mkv"
            original.write_bytes(b"sample")
            symlink = Path(d) / "link.mkv"
            symlink.symlink_to(original)
            with self.assertRaises(ValueError):
                probe_local_sample(symlink)

    def test_malformed_probe_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            sample = Path(d) / "sample.mkv"
            sample.write_bytes(b"sample")
            report = probe_local_sample(sample, which=lambda _: "/usr/bin/ffprobe",
                                        runner=lambda *a, **kw: SimpleNamespace(returncode=0, stdout=b"not-json"))
            self.assertEqual(report["status"], "PROBE_FAILED")
            self.assertFalse(report["review_approved"])
